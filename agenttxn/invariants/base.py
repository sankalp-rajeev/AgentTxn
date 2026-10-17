"""Week-one deterministic business invariants."""

from agenttxn.effects.certainty import Certainty
from agenttxn.effects.models import (
    Certification,
    Decision,
    EffectIntent,
    EffectRecord,
    Operation,
)

RESERVED = frozenset({Certainty.PENDING, Certainty.UNKNOWN, Certainty.CONFIRMED})


def shipment_requires_confirmed_payment(
    effects: list[EffectRecord],
    intent: EffectIntent,
) -> Certification:
    name = ("shipment_requires_confirmed_payment",)
    payments = [
        record
        for record in effects
        if record.intent.operation == Operation.CHARGE and record.intent.order_id == intent.order_id
    ]
    if any(record.certainty == Certainty.CONFIRMED for record in payments):
        return Certification(decision=Decision.COMMIT, reason="Payment confirmed", invariants=name)
    unresolved = tuple(
        record.intent.effect_id for record in payments if record.certainty == Certainty.UNKNOWN
    )
    if unresolved:
        return Certification(
            decision=Decision.RECONCILE,
            reason="Payment outcome is ambiguous",
            invariants=name,
            blocking_effect_ids=unresolved,
        )
    if any(record.certainty in {Certainty.NOT_STARTED, Certainty.PENDING} for record in payments):
        return Certification(
            decision=Decision.WAIT,
            reason="Payment has not settled",
            invariants=name,
            blocking_effect_ids=tuple(record.intent.effect_id for record in payments),
        )
    return Certification(decision=Decision.BLOCK, reason="No confirmed payment", invariants=name)


def incident_compensation_cap(
    effects: list[EffectRecord],
    intent: EffectIntent,
    budget_cents: int,
) -> Certification:
    total = sum(
        record.intent.amount_cents
        for record in effects
        if record.intent.effect_id != intent.effect_id
        and record.intent.incident_id == intent.incident_id
        and record.intent.operation in {Operation.REFUND, Operation.CREDIT}
        and record.certainty in RESERVED
    )
    return Certification(
        decision=Decision.COMMIT if total + intent.amount_cents <= budget_cents else Decision.BLOCK,
        reason=f"Reserved plus proposed compensation: {total + intent.amount_cents}/{budget_cents}",
        invariants=("incident_compensation_cap",),
    )
