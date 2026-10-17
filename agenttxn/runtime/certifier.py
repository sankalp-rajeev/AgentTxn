"""Certify week-one invariants over committed and reserved effects."""

from agenttxn.effects.certainty import Certainty
from agenttxn.effects.ledger import Ledger
from agenttxn.effects.models import Certification, Decision, EffectIntent, Operation
from agenttxn.invariants.base import incident_compensation_cap, shipment_requires_confirmed_payment


class SemanticCertifier:
    def __init__(self, budgets: dict[str, int]) -> None:
        self.budgets = dict(budgets)

    def keys(self, intent: EffectIntent) -> tuple[str, ...]:
        if intent.operation in {Operation.CHARGE, Operation.SHIP}:
            return (f"order:{intent.order_id}",)
        return (f"incident:{intent.incident_id}",)

    async def certify(self, intent: EffectIntent, ledger: Ledger) -> Certification:
        effects = await ledger.effects()
        if intent.dependencies:
            by_id = {record.intent.effect_id: record for record in effects}
            if any(effect_id not in by_id for effect_id in intent.dependencies):
                return Certification(decision=Decision.BLOCK, reason="Missing declared dependency")
            required = [by_id[effect_id] for effect_id in intent.dependencies]
            if any(
                item.certainty in {Certainty.FAILED, Certainty.COMPENSATED} for item in required
            ):
                return Certification(decision=Decision.BLOCK, reason="Declared dependency failed")
            unknown = tuple(
                item.intent.effect_id for item in required if item.certainty == Certainty.UNKNOWN
            )
            if unknown:
                return Certification(
                    decision=Decision.RECONCILE,
                    reason="Declared dependency is ambiguous",
                    blocking_effect_ids=unknown,
                )
            pending = tuple(
                item.intent.effect_id
                for item in required
                if item.certainty in {Certainty.NOT_STARTED, Certainty.PENDING}
            )
            if pending:
                return Certification(
                    decision=Decision.WAIT,
                    reason="Declared dependency has not settled",
                    blocking_effect_ids=pending,
                )
        if intent.operation == Operation.SHIP:
            return shipment_requires_confirmed_payment(effects, intent)
        if intent.operation in {Operation.REFUND, Operation.CREDIT}:
            if intent.incident_id not in self.budgets:
                return Certification(decision=Decision.BLOCK, reason="No declared incident budget")
            return incident_compensation_cap(effects, intent, self.budgets[str(intent.incident_id)])
        return Certification(decision=Decision.COMMIT, reason="No additional charge invariant")
