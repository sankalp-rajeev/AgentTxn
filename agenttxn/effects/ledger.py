"""Ledger contract and deterministic in-memory reference implementation."""

import asyncio
from typing import Protocol

from agenttxn.effects.certainty import Certainty, validate_transition
from agenttxn.effects.models import Certification, EffectIntent, EffectRecord, LedgerEvent
from agenttxn.effects.outcomes import ExternalOutcome, OutcomeSet, validate_refinement


class Ledger(Protocol):
    run_id: str

    async def register(self, intent: EffectIntent) -> EffectRecord: ...
    async def get(self, effect_id: str) -> EffectRecord: ...
    async def effects(self) -> list[EffectRecord]: ...
    async def transition(
        self, effect_id: str, after: Certainty, reason: str, observation: str | None = None
    ) -> EffectRecord: ...
    async def decide(self, effect_id: str, result: Certification) -> None: ...
    async def events(self) -> list[LedgerEvent]: ...
    async def refine_outcomes(
        self, effect_id: str, outcomes: OutcomeSet, evidence: str
    ) -> EffectRecord: ...
    async def close(self) -> None: ...


def make_event(
    run_id: str,
    record: EffectRecord,
    reason: str,
    event_type: str,
    *,
    before: Certainty | None = None,
    result: Certification | None = None,
    observation: str | None = None,
) -> LedgerEvent:
    intent = record.intent
    return LedgerEvent(
        sequence=0,
        run_id=run_id,
        transaction_id=intent.transaction_id,
        agent_id=intent.agent_id,
        effect_id=intent.effect_id,
        operation=intent.operation,
        event_type=event_type,
        certainty_state_before=before,
        certainty_state_after=record.certainty,
        decision=result.decision if result else None,
        reason=reason,
        relevant_invariants=result.invariants if result else (),
        blocking_effect_ids=result.blocking_effect_ids if result else (),
        observation=observation,
        possible_outcomes=record.possible_outcomes,
    )


def refine_record(record: EffectRecord, outcomes: OutcomeSet) -> EffectRecord:
    if record.certainty not in {Certainty.UNKNOWN, Certainty.CONFIRMED, Certainty.FAILED}:
        raise ValueError("Outcome evidence requires an observed external request")
    validate_refinement(record.possible_outcomes, outcomes)
    after = Certainty.UNKNOWN
    if outcomes.terminal:
        after = (
            Certainty.CONFIRMED
            if outcomes.contains(ExternalOutcome.COMMITTED)
            else Certainty.FAILED
        )
    if after != record.certainty:
        validate_transition(record.certainty, after)
    return record.model_copy(update={"certainty": after, "possible_outcomes": outcomes})


class MemoryLedger:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._records: dict[str, EffectRecord] = {}
        self._events: list[LedgerEvent] = []
        self._lock = asyncio.Lock()

    def _append(self, event: LedgerEvent) -> None:
        self._events.append(event.model_copy(update={"sequence": len(self._events) + 1}))

    async def register(self, intent: EffectIntent) -> EffectRecord:
        async with self._lock:
            existing = self._records.get(intent.effect_id)
            if existing:
                if existing.intent != intent:
                    raise ValueError("Effect identity was reused with different arguments")
                return existing.model_copy(deep=True)
            if any(
                item.intent.logical_operation_id == intent.logical_operation_id
                for item in self._records.values()
            ):
                raise ValueError(
                    "Logical operation already registered with another effect identity"
                )
            record = EffectRecord(intent=intent.model_copy(deep=True))
            self._records[intent.effect_id] = record
            self._append(make_event(self.run_id, record, "Intent registered", "registered"))
            return record.model_copy(deep=True)

    async def get(self, effect_id: str) -> EffectRecord:
        async with self._lock:
            return self._records[effect_id].model_copy(deep=True)

    async def effects(self) -> list[EffectRecord]:
        async with self._lock:
            return [record.model_copy(deep=True) for record in self._records.values()]

    async def transition(
        self, effect_id: str, after: Certainty, reason: str, observation: str | None = None
    ) -> EffectRecord:
        async with self._lock:
            record = self._records[effect_id]
            validate_transition(record.certainty, after)
            updated = record.model_copy(update={"certainty": after})
            self._records[effect_id] = updated
            self._append(
                make_event(
                    self.run_id,
                    updated,
                    reason,
                    "transition",
                    before=record.certainty,
                    observation=observation,
                )
            )
            return updated.model_copy(deep=True)

    async def decide(self, effect_id: str, result: Certification) -> None:
        async with self._lock:
            self._append(
                make_event(
                    self.run_id, self._records[effect_id], result.reason, "decision", result=result
                )
            )

    async def events(self) -> list[LedgerEvent]:
        async with self._lock:
            return [event.model_copy(deep=True) for event in self._events]

    async def refine_outcomes(
        self, effect_id: str, outcomes: OutcomeSet, evidence: str
    ) -> EffectRecord:
        async with self._lock:
            before = self._records[effect_id]
            updated = refine_record(before, outcomes)
            self._records[effect_id] = updated
            self._append(
                make_event(
                    self.run_id,
                    updated,
                    evidence,
                    "outcome_observation",
                    before=before.certainty,
                    observation=evidence,
                )
            )
            return updated.model_copy(deep=True)

    async def close(self) -> None:
        return None
