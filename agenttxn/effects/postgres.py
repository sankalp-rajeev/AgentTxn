"""PostgreSQL ledger with atomic observation/state/event writes and row locking."""

import hashlib
from importlib.resources import files

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from agenttxn.effects.certainty import Certainty, validate_transition
from agenttxn.effects.ledger import make_event
from agenttxn.effects.models import Certification, EffectIntent, EffectRecord, LedgerEvent


class PostgresLedger:
    def __init__(self, database_url: str, run_id: str) -> None:
        if not database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("The persistent ledger requires a postgresql+asyncpg URL")
        self.run_id = run_id
        self.engine: AsyncEngine = create_async_engine(database_url)

    async def migrate(self) -> None:
        source = files("agenttxn.effects").joinpath("migrations/0001_effect_ledger.sql")
        sql = source.read_text(encoding="utf-8")
        digest = hashlib.sha256(sql.encode()).hexdigest()
        async with self.engine.begin() as conn:
            # A transaction-scoped lock protects concurrent migration attempts.
            await conn.execute(text("SELECT pg_advisory_xact_lock(72304101)"))
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS agenttxn_schema_migrations "
                    "(version INTEGER PRIMARY KEY, checksum TEXT NOT NULL)"
                )
            )
            existing = await conn.scalar(
                text("SELECT checksum FROM agenttxn_schema_migrations WHERE version = 1")
            )
            if existing is not None:
                if existing != digest:
                    raise ValueError("Applied migration checksum differs from source")
                return
            raw = await conn.get_raw_connection()
            # asyncpg's execute accepts the multi-statement migration in this transaction.
            driver = raw.driver_connection
            if driver is None:
                raise RuntimeError("PostgreSQL driver connection is unavailable")
            await driver.execute(sql)
            await conn.execute(
                text("INSERT INTO agenttxn_schema_migrations VALUES (1, :checksum)"),
                {"checksum": digest},
            )

    async def _event(self, conn: AsyncConnection, event: LedgerEvent) -> None:
        await conn.execute(
            text(
                "INSERT INTO effect_events(run_id, effect_id, event) "
                "VALUES (:run_id, :effect_id, CAST(:event AS JSONB))"
            ),
            {"run_id": self.run_id, "effect_id": event.effect_id, "event": event.model_dump_json()},
        )

    def _params(self, effect_id: str) -> dict[str, str]:
        return {"run_id": self.run_id, "effect_id": effect_id}

    async def _get(
        self, conn: AsyncConnection, effect_id: str, *, lock: bool = False
    ) -> EffectRecord:
        suffix = " FOR UPDATE" if lock else ""
        row = (
            (
                await conn.execute(
                    text(
                        "SELECT intent, certainty FROM effect_intents "
                        "WHERE run_id = :run_id AND effect_id = :effect_id" + suffix
                    ),
                    self._params(effect_id),
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise KeyError(effect_id)
        return EffectRecord(
            intent=EffectIntent.model_validate(row["intent"]), certainty=Certainty(row["certainty"])
        )

    async def register(self, intent: EffectIntent) -> EffectRecord:
        params = {
            **self._params(intent.effect_id),
            "transaction_id": intent.transaction_id,
            "logical_operation_id": intent.logical_operation_id,
            "agent_id": intent.agent_id,
            "workflow_id": intent.workflow_id,
            "intent": intent.model_dump_json(),
            "certainty": Certainty.NOT_STARTED.value,
        }
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO transactions VALUES "
                    "(:run_id, :transaction_id, :agent_id, :workflow_id) ON CONFLICT DO NOTHING"
                ),
                params,
            )
            inserted = await conn.scalar(
                text(
                    "INSERT INTO effect_intents "
                    "(run_id, effect_id, transaction_id, logical_operation_id, intent, certainty) "
                    "VALUES (:run_id, :effect_id, :transaction_id, :logical_operation_id, "
                    "CAST(:intent AS JSONB), :certainty) "
                    "ON CONFLICT (run_id, effect_id) DO NOTHING RETURNING effect_id"
                ),
                params,
            )
            record = await self._get(conn, intent.effect_id)
            if record.intent != intent:
                raise ValueError("Effect identity was reused with different arguments")
            if inserted is not None:
                await self._event(
                    conn, make_event(self.run_id, record, "Intent registered", "registered")
                )
            return record

    async def get(self, effect_id: str) -> EffectRecord:
        async with self.engine.connect() as conn:
            return await self._get(conn, effect_id)

    async def effects(self) -> list[EffectRecord]:
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT intent, certainty FROM effect_intents "
                        "WHERE run_id = :run_id ORDER BY effect_id"
                    ),
                    {"run_id": self.run_id},
                )
            ).mappings()
            return [
                EffectRecord(
                    intent=EffectIntent.model_validate(row["intent"]),
                    certainty=Certainty(row["certainty"]),
                )
                for row in rows
            ]

    async def transition(
        self, effect_id: str, after: Certainty, reason: str, observation: str | None = None
    ) -> EffectRecord:
        async with self.engine.begin() as conn:
            before = await self._get(conn, effect_id, lock=True)
            validate_transition(before.certainty, after)
            updated = before.model_copy(update={"certainty": after})
            await conn.execute(
                text(
                    "UPDATE effect_intents SET certainty = :certainty "
                    "WHERE run_id = :run_id AND effect_id = :effect_id"
                ),
                {**self._params(effect_id), "certainty": after.value},
            )
            if observation is not None:
                await conn.execute(
                    text(
                        "INSERT INTO effect_observations(run_id, effect_id, observation) "
                        "VALUES (:run_id, :effect_id, :observation)"
                    ),
                    {**self._params(effect_id), "observation": observation},
                )
            await self._event(
                conn,
                make_event(
                    self.run_id,
                    updated,
                    reason,
                    "transition",
                    before=before.certainty,
                    observation=observation,
                ),
            )
            return updated

    async def decide(self, effect_id: str, result: Certification) -> None:
        async with self.engine.begin() as conn:
            record = await self._get(conn, effect_id, lock=True)
            await self._event(
                conn,
                make_event(
                    self.run_id,
                    record,
                    result.reason,
                    "decision",
                    result=result,
                ),
            )

    async def events(self) -> list[LedgerEvent]:
        async with self.engine.connect() as conn:
            rows = await conn.scalars(
                text("SELECT event FROM effect_events WHERE run_id = :run_id ORDER BY event_id"),
                {"run_id": self.run_id},
            )
            return [
                LedgerEvent.model_validate(event).model_copy(update={"sequence": index})
                for index, event in enumerate(rows, start=1)
            ]

    async def close(self) -> None:
        await self.engine.dispose()
