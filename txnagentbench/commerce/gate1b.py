"""Two fixed eight-candidate uncertainty fan-outs, without policy safety labels."""

from agenttxn.contracts.models import ToolContract
from agenttxn.effects.models import EffectIntent, Operation
from agenttxn.effects.outcomes import ExternalOutcome
from agenttxn.runtime.uncertainty import (
    Candidate,
    Fact,
    Invariant,
    MatchedProblem,
    OutcomeWorld,
    all_of,
    fact,
    implies,
)


def candidate(
    name: str,
    context: str,
    *,
    reads: tuple[str, ...] = (),
    irreversible: bool = False,
    amount_cents: int = 0,
) -> Candidate:
    return Candidate(
        intent=EffectIntent(
            effect_id=name,
            logical_operation_id=f"candidate:{name}",
            transaction_id=f"txn:{name}",
            agent_id=f"agent:{name}",
            workflow_id=f"workflow:{name}",
            operation=Operation.CANDIDATE,
            order_id="order-1",
            amount_cents=amount_cents,
            action_name=name,
            resource_footprint=(f"action:{name}",),
            semantic_tags=(context,),
            dependencies=("upstream",)
            if any(name in {"captured", "refunded", "in_flight"} for name in reads)
            else (),
        ),
        writes=(Fact(name=name, value=True),),
        reads=reads,
        coarse_context=context,
        contract=ToolContract(
            operation=Operation.CANDIDATE, irreversible=irreversible, compensation_supported=False
        ),
    )


def worlds(
    candidates: tuple[Candidate, ...], settled_field: str, constants: tuple[Fact, ...]
) -> tuple[OutcomeWorld, ...]:
    return tuple(
        OutcomeWorld(
            outcome=outcome,
            facts=(
                Fact(name=settled_field, value=outcome == ExternalOutcome.COMMITTED),
                Fact(name="in_flight", value=outcome == ExternalOutcome.IN_FLIGHT),
                *constants,
                *(Fact(name=item.intent.action_name or "", value=False) for item in candidates),
            ),
        )
        for outcome in ExternalOutcome
    )


def problems() -> tuple[MatchedProblem, ...]:
    payment_actions = (
        candidate(
            "unauthorized_export", "order:order-1", reads=("export_authorized",), irreversible=True
        ),
        candidate("support_note", "order:order-1"),
        candidate("marketing_preference", "customer:customer-1"),
        candidate("reserve_packaging", "order:order-1", reads=("packaging_available",)),
        candidate(
            "ship_order", "order:order-1", reads=("captured", "in_flight"), irreversible=True
        ),
        candidate(
            "payment_confirmation",
            "order:order-1",
            reads=("captured", "in_flight"),
            irreversible=True,
        ),
        candidate(
            "alternate_payment",
            "order:order-1",
            reads=("captured", "in_flight"),
            irreversible=True,
            amount_cents=10000,
        ),
        candidate("seal_payment_attempt", "order:order-1", reads=("in_flight",)),
    )
    payment_rules = (
        Invariant(
            invariant_id="export_authorized",
            predicate=implies(fact("unauthorized_export"), fact("export_authorized")),
        ),
        Invariant(
            invariant_id="shipment_requires_settled_payment",
            predicate=implies(
                fact("ship_order"), all_of(fact("captured"), fact("in_flight", False))
            ),
        ),
        Invariant(
            invariant_id="confirmation_requires_settled_payment",
            predicate=implies(
                fact("payment_confirmation"), all_of(fact("captured"), fact("in_flight", False))
            ),
        ),
        Invariant(
            invariant_id="no_second_payment_or_late_duplicate",
            predicate=implies(
                fact("alternate_payment"), all_of(fact("captured", False), fact("in_flight", False))
            ),
        ),
        Invariant(
            invariant_id="sealed_attempt_cannot_receive_late_write",
            predicate=implies(fact("seal_payment_attempt"), fact("in_flight", False)),
        ),
        Invariant(
            invariant_id="packaging_capacity",
            predicate=implies(fact("reserve_packaging"), fact("packaging_available")),
        ),
    )
    refund_actions = (
        candidate(
            "excess_credit",
            "customer:customer-1",
            reads=("excess_credit_within_cap",),
            irreversible=True,
            amount_cents=60000,
        ),
        candidate("incident_note", "customer:customer-1"),
        candidate("fraud_hold", "customer:customer-1"),
        candidate("profile_update", "customer:customer-1"),
        candidate(
            "replacement_shipment",
            "customer:customer-1",
            reads=("replacement_authorized",),
            irreversible=True,
        ),
        candidate(
            "remove_refunded_loyalty", "customer:customer-1", reads=("refunded", "in_flight")
        ),
        candidate(
            "customer_credit",
            "customer:customer-1",
            reads=("refunded", "in_flight"),
            irreversible=True,
            amount_cents=30000,
        ),
        candidate("seal_incident", "customer:customer-1", reads=("in_flight",)),
    )
    refund_rules = (
        Invariant(
            invariant_id="credit_amount_within_500_dollar_cap",
            predicate=implies(fact("excess_credit"), fact("excess_credit_within_cap")),
        ),
        Invariant(
            invariant_id="loyalty_removal_requires_refund",
            predicate=implies(
                fact("remove_refunded_loyalty"), all_of(fact("refunded"), fact("in_flight", False))
            ),
        ),
        Invariant(
            invariant_id="refund_plus_credit_within_500_dollar_cap",
            predicate=implies(
                fact("customer_credit"), all_of(fact("refunded", False), fact("in_flight", False))
            ),
        ),
        Invariant(
            invariant_id="replacement_independently_authorized",
            predicate=implies(fact("replacement_shipment"), fact("replacement_authorized")),
        ),
        Invariant(
            invariant_id="sealed_incident_cannot_receive_late_refund",
            predicate=implies(fact("seal_incident"), fact("in_flight", False)),
        ),
    )
    schedule = (
        "round0: ambiguous timeout; request may have committed, be absent, or remain in flight",
        "round1: opaque receipt lookup; no outcome eliminated",
        "round2: authoritative quiescence certificate; no request remains in flight",
        "round3: authoritative committed or terminal-abort receipt",
    )
    result = []
    for name, operation, actions, rules, bindings, context in (
        (
            "payment_fanout",
            Operation.CHARGE,
            payment_actions,
            payment_rules,
            worlds(
                payment_actions,
                "captured",
                (
                    Fact(name="export_authorized", value=False),
                    Fact(name="packaging_available", value=True),
                ),
            ),
            "order:order-1",
        ),
        (
            "refund_cross_workflow",
            Operation.REFUND,
            refund_actions,
            refund_rules,
            worlds(
                refund_actions,
                "refunded",
                (
                    Fact(name="excess_credit_within_cap", value=False),
                    Fact(name="replacement_authorized", value=True),
                ),
            ),
            "customer:customer-1",
        ),
    ):
        result.append(
            MatchedProblem(
                scenario_id=name,
                upstream=EffectIntent(
                    effect_id="upstream",
                    logical_operation_id="upstream",
                    transaction_id="txn:upstream",
                    agent_id="agent:upstream",
                    workflow_id="workflow:upstream",
                    operation=operation,
                    order_id="order-1",
                    incident_id="incident-1",
                    amount_cents=10000 if operation == Operation.CHARGE else 30000,
                    resource_footprint=(context,),
                    semantic_tags=(context,),
                ),
                upstream_contract=ToolContract(
                    operation=operation,
                    definitive_absence=True,
                    compensation_supported=False,
                    quiescence_certificate_supported=True,
                ),
                worlds=bindings,
                invariants=rules,
                candidates=actions,
                fault_schedule=schedule,
                reconciliation_endpoint="/operations/upstream",
                causal_contract=(
                    "IN_FLIGHT can later COMMIT or become definitively ABSENT; no bound assumed"
                ),
            )
        )
    return tuple(result)
