"""Controlled week-one scenarios; seeded launch order, explicit ambiguity twins."""

import random

from agenttxn.contracts.models import week1_contracts
from agenttxn.effects.models import EffectIntent, Operation
from agenttxn.faults.injector import Fault
from txnagentbench.schema import Scenario


def financial_intent(
    operation: Operation,
    effect_id: str,
    incident_id: str = "incident-1",
    amount_cents: int = 30000,
) -> EffectIntent:
    return EffectIntent(
        effect_id=effect_id,
        logical_operation_id=effect_id,
        transaction_id=f"txn:{effect_id}",
        agent_id=f"agent:{effect_id}",
        workflow_id=f"workflow:{effect_id}",
        operation=operation,
        incident_id=incident_id,
        amount_cents=amount_cents,
        resource_footprint=(f"{operation}:{effect_id}",),
    )


def scenarios(seed: int) -> list[Scenario]:
    payment = EffectIntent(
        effect_id="charge-1",
        logical_operation_id="charge-1",
        transaction_id="txn:charge",
        agent_id="agent:payment",
        workflow_id="workflow:payment",
        operation=Operation.CHARGE,
        order_id="order-1",
        amount_cents=10000,
        resource_footprint=("payment:order-1",),
    )
    shipment = EffectIntent(
        effect_id="ship-1",
        logical_operation_id="ship-1",
        transaction_id="txn:ship",
        agent_id="agent:shipping",
        workflow_id="workflow:shipping",
        operation=Operation.SHIP,
        order_id="order-1",
        resource_footprint=("shipment:order-1",),
        read_versions={"payment:order-1": 0},
        dependencies=("charge-1",),
    )
    contracts = tuple(week1_contracts().values())
    result = []
    for fault in (Fault.TIMEOUT_AFTER_EFFECT, Fault.TIMEOUT_BEFORE_EFFECT):
        result.append(
            Scenario(
                scenario_id=f"ambiguous_payment_{fault.value.removeprefix('timeout_')}",
                domain="commerce",
                initial_state={"payment": "absent", "shipment": "absent"},
                agents=(payment.agent_id, shipment.agent_id),
                workflows=(payment, shipment),
                tool_contracts=contracts,
                semantic_invariants=("shipment_requires_confirmed_payment",),
                fault_schedule={payment.logical_operation_id: fault},
                success_conditions=(
                    "Do not dispatch shipment without confirmed prerequisite evidence",
                ),
                forbidden_states=(
                    "Shipment without a real charge",
                    "Shipment while charge is UNKNOWN",
                ),
                expected_serial_outcome=(
                    "One charge and one shipment after reconciliation"
                    if fault == Fault.TIMEOUT_AFTER_EFFECT
                    else "No charge or shipment; payment failure resolved by definitive probe"
                ),
                budgets_cents={},
            )
        )
    for independent in (False, True):
        intents = [
            financial_intent(Operation.REFUND, "refund-1"),
            financial_intent(
                Operation.CREDIT, "credit-1", "incident-2" if independent else "incident-1"
            ),
        ]
        random.Random(seed).shuffle(intents)
        budgets = {"incident-1": 50000}
        if independent:
            budgets["incident-2"] = 50000
        result.append(
            Scenario(
                scenario_id="independent_compensation"
                if independent
                else "disjoint_resource_compensation",
                domain="commerce",
                initial_state={"committed_compensation_cents": 0},
                agents=tuple(intent.agent_id for intent in intents),
                workflows=tuple(intents),
                tool_contracts=contracts,
                semantic_invariants=("incident_compensation_cap",),
                fault_schedule={},
                budgets_cents=budgets,
                success_conditions=(
                    "Respect each incident budget",
                    "Admit independent work concurrently",
                ),
                forbidden_states=("Committed compensation exceeds an incident budget",),
                expected_serial_outcome="Two effects on separate incidents"
                if independent
                else "Exactly one 30000-cent compensation effect under a 50000-cent budget",
                require_provider_overlap=2 if independent else 0,
            )
        )
    return result
