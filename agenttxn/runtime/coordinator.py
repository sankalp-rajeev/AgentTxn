"""Single-coordinator admission; external calls never hold certification locks."""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Protocol

from agenttxn.adapters.direct import DirectAdapter
from agenttxn.contracts.models import ToolOutcome
from agenttxn.effects.certainty import Certainty
from agenttxn.effects.ledger import Ledger
from agenttxn.effects.models import Certification, Decision, EffectIntent, EffectRecord


class AdmissionPolicy(Protocol):
    def keys(self, intent: EffectIntent) -> tuple[str, ...]: ...
    async def certify(self, intent: EffectIntent, ledger: Ledger) -> Certification: ...


class Coordinator:
    """Supports concurrent tasks in one process, not distributed admission leaders."""

    def __init__(
        self,
        ledger: Ledger,
        adapter: DirectAdapter,
        policy: AdmissionPolicy,
        on_admission: Callable[[EffectIntent], None] | None = None,
    ) -> None:
        self.ledger = ledger
        self.adapter = adapter
        self.policy = policy
        self._locks: dict[str, asyncio.Lock] = {}
        self._effect_locks: dict[str, asyncio.Lock] = {}
        self._changed = asyncio.Condition()
        self._generation = 0
        self._on_admission = on_admission

    async def _notify(self) -> None:
        async with self._changed:
            self._generation += 1
            self._changed.notify_all()

    async def _wait_for_change(self, generation: int, budget_seconds: float) -> None:
        async with self._changed:
            await asyncio.wait_for(
                self._changed.wait_for(lambda: self._generation != generation),
                timeout=budget_seconds,
            )

    async def _resolve(self, effect_id: str) -> ToolOutcome:
        async with self._effect_locks.setdefault(effect_id, asyncio.Lock()):
            record = await self.ledger.get(effect_id)
            if record.certainty != Certainty.UNKNOWN:
                return ToolOutcome(certainty=record.certainty, reason="Already settled")
            outcome = await self.adapter.reconcile(record.intent)
            if outcome.certainty in {Certainty.CONFIRMED, Certainty.FAILED}:
                await self.ledger.transition(
                    effect_id,
                    outcome.certainty,
                    "Reconciliation provided evidence",
                    outcome.model_dump_json(),
                )
                await self._notify()
            return outcome

    async def reconcile(self, effect_id: str) -> ToolOutcome:
        return await self._resolve(effect_id)

    async def submit(self, intent: EffectIntent, *, wait_timeout: float = 5.0) -> Certification:
        async with self._effect_locks.setdefault(intent.effect_id, asyncio.Lock()):
            record = await self.ledger.register(intent)
            if record.certainty != Certainty.NOT_STARTED:
                result = Certification(
                    decision=Decision.COMMIT
                    if record.certainty == Certainty.CONFIRMED
                    else Decision.HUMAN_REVIEW,
                    reason=f"Existing effect is {record.certainty}; not executed again",
                )
                await self.ledger.decide(intent.effect_id, result)
                return result
            while True:
                generation = self._generation
                async with AsyncExitStack() as stack:
                    for key in sorted(set(self.policy.keys(intent))):
                        await stack.enter_async_context(self._locks.setdefault(key, asyncio.Lock()))
                    result = await self.policy.certify(intent, self.ledger)
                    await self.ledger.decide(intent.effect_id, result)
                    if result.decision == Decision.COMMIT:
                        await self.ledger.transition(
                            intent.effect_id, Certainty.PENDING, result.reason
                        )
                if self._on_admission is not None:
                    self._on_admission(intent)
                if result.decision == Decision.RECONCILE:
                    outcomes = [
                        await self._resolve(effect_id) for effect_id in result.blocking_effect_ids
                    ]
                    if not outcomes or any(
                        item.certainty == Certainty.UNKNOWN for item in outcomes
                    ):
                        result = Certification(
                            decision=Decision.HUMAN_REVIEW,
                            reason="Prerequisite cannot be resolved",
                            invariants=result.invariants,
                            blocking_effect_ids=result.blocking_effect_ids,
                        )
                        await self.ledger.decide(intent.effect_id, result)
                        return result
                    continue
                if result.decision == Decision.WAIT:
                    try:
                        await self._wait_for_change(generation, wait_timeout)
                    except TimeoutError:
                        result = Certification(
                            decision=Decision.HUMAN_REVIEW,
                            reason="Prerequisite wait budget exhausted",
                            invariants=result.invariants,
                            blocking_effect_ids=result.blocking_effect_ids,
                        )
                        await self.ledger.decide(intent.effect_id, result)
                        return result
                    continue
                if result.decision != Decision.COMMIT:
                    return result
                try:
                    outcome = await self.adapter.execute(intent)
                except asyncio.CancelledError:
                    await self.ledger.transition(
                        intent.effect_id, Certainty.UNKNOWN, "Cancelled after request admission"
                    )
                    await self._notify()
                    raise
                await self.ledger.transition(
                    intent.effect_id,
                    outcome.certainty,
                    "Tool observation",
                    outcome.model_dump_json(),
                )
                await self._notify()
                return result

    async def record(self, effect_id: str) -> EffectRecord:
        return await self.ledger.get(effect_id)
