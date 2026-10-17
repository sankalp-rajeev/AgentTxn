"""Evaluate provider truth independently; distinguish physical and evidence safety."""

from pydantic import BaseModel

from agenttxn.effects.certainty import Certainty
from agenttxn.effects.models import Decision, EffectRecord, LedgerEvent, Operation
from services.common import ProviderEffect
from txnagentbench.schema import Scenario


class Metrics(BaseModel):
    invariant_violations: int
    unsafe_downstream_actions: int
    committed_external_effects: int
    confirmed_local_effects: int
    unresolved_unknown_effects: int
    duplicate_effects: int
    blocked_intents: int
    reconciliation_decisions: int
    max_provider_calls_in_flight: int
    task_success: bool


def evaluate(
    scenario: Scenario,
    records: list[EffectRecord],
    events: list[LedgerEvent],
    journal: list[ProviderEffect],
    max_in_flight: int,
) -> Metrics:
    physical_violations = 0
    paid: set[str | None] = set()
    totals: dict[str, int] = {}
    for effect in journal:
        if effect.operation == Operation.CHARGE:
            paid.add(effect.request.order_id)
        elif effect.operation == Operation.SHIP:
            physical_violations += effect.request.order_id not in paid
        elif effect.operation in {Operation.REFUND, Operation.CREDIT}:
            incident = str(effect.request.incident_id)
            totals[incident] = totals.get(incident, 0) + effect.request.amount_cents
            physical_violations += totals[incident] > scenario.budgets_cents[incident]
    by_id = {record.intent.effect_id: record.intent for record in records}
    certainty: dict[str, Certainty] = {}
    unsafe = 0
    for event in events:
        if (
            event.operation == Operation.SHIP
            and event.event_type == "transition"
            and (event.certainty_state_after == Certainty.PENDING)
        ):
            order_id = by_id[event.effect_id].order_id
            known_paid = any(
                intent.operation == Operation.CHARGE
                and intent.order_id == order_id
                and certainty.get(effect_id) == Certainty.CONFIRMED
                for effect_id, intent in by_id.items()
            )
            unsafe += not known_paid
        certainty[event.effect_id] = event.certainty_state_after
    unique = {(effect.operation, effect.request.logical_operation_id) for effect in journal}
    confirmed = sum(record.certainty == Certainty.CONFIRMED for record in records)
    unknown = sum(record.certainty == Certainty.UNKNOWN for record in records)
    if scenario.scenario_id == "ambiguous_payment_after_effect":
        complete = len(journal) == 2 and confirmed == 2
    elif scenario.scenario_id == "ambiguous_payment_before_effect":
        complete = not journal and any(record.certainty == Certainty.FAILED for record in records)
    else:
        complete = len(journal) == (2 if scenario.require_provider_overlap else 1)
    return Metrics(
        invariant_violations=physical_violations,
        unsafe_downstream_actions=unsafe,
        committed_external_effects=len(journal),
        confirmed_local_effects=confirmed,
        unresolved_unknown_effects=unknown,
        duplicate_effects=len(journal) - len(unique),
        blocked_intents=len(
            {
                event.effect_id
                for event in events
                if event.decision in {Decision.BLOCK, Decision.HUMAN_REVIEW}
            }
        ),
        reconciliation_decisions=sum(event.decision == Decision.RECONCILE for event in events),
        max_provider_calls_in_flight=max_in_flight,
        task_success=complete and physical_violations == 0 and unsafe == 0,
    )
