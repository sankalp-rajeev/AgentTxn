from itertools import combinations

import pytest

from agenttxn.effects.models import Decision
from agenttxn.effects.outcomes import ALL_OUTCOMES, QUIESCENT_OUTCOMES, ExternalOutcome, OutcomeSet
from agenttxn.runtime.outcome_admission import OutcomeConditionedAdmission
from agenttxn.runtime.uncertainty import AdmissionView, Observation
from baselines.uncertainty import POLICIES, GlobalFailClosed, compile_scopes
from txnagentbench.commerce.gate1b import problems
from txnagentbench.oracle import joint_subset_audit, oracle_safe, safe_outcomes, violations


def view(index: int, outcomes: OutcomeSet) -> AdmissionView:
    return AdmissionView(
        problem=problems()[index],
        observations=(Observation(round=0, description="Evidence snapshot", outcomes=outcomes),),
    )


@pytest.mark.parametrize("index", [0, 1])
def test_all_five_required_action_classes_exist_without_policy_labels(index: int) -> None:
    problem = problems()[index]
    classes = {frozenset(safe_outcomes(problem, item)) for item in problem.candidates}
    assert classes == {
        frozenset(),
        frozenset(ExternalOutcome),
        frozenset({ExternalOutcome.COMMITTED}),
        frozenset({ExternalOutcome.ABSENT}),
        frozenset({ExternalOutcome.COMMITTED, ExternalOutcome.ABSENT}),
    }
    for item in problem.candidates:
        assert "safety_class" not in item.model_dump()


@pytest.mark.parametrize("index", [0, 1])
def test_exhaustive_outcome_subsets_and_strong_policy_equivalence(index: int) -> None:
    for size in range(1, 4):
        for values in combinations(tuple(ExternalOutcome), size):
            context = view(index, OutcomeSet(values=values))
            policies = [policy(context) for policy in POLICIES]
            assert joint_subset_audit(context.problem, context.outcomes) >= 1
            for candidate in context.problem.candidates:
                expected = policies[-1].assess(candidate).decision
                assert (expected == Decision.COMMIT) == oracle_safe(
                    context.problem, candidate, context.outcomes
                )
                assert all(policy.assess(candidate).decision == expected for policy in policies[1:])
                for policy in policies:
                    if policy.assess(candidate).decision == Decision.COMMIT:
                        assert oracle_safe(context.problem, candidate, context.outcomes)


def test_safe_same_order_note_does_not_need_an_uncertain_payment_scope() -> None:
    context = view(0, ALL_OUTCOMES)
    candidate = next(
        item for item in context.problem.candidates if item.intent.action_name == "support_note"
    )
    assert candidate.coarse_context == context.problem.upstream.resource_footprint[0]
    assert compile_scopes(context.problem, candidate) == ()
    assert GlobalFailClosed(context).assess(candidate).decision == Decision.WAIT
    assert all(
        policy(context).assess(candidate).decision == Decision.COMMIT for policy in POLICIES[1:]
    )


def test_quiescence_is_distinct_from_absence_and_makes_sealing_safe() -> None:
    initial = view(0, ALL_OUTCOMES)
    quiescent = view(0, QUIESCENT_OUTCOMES)
    candidate = next(
        item
        for item in initial.problem.candidates
        if item.intent.action_name == "seal_payment_attempt"
    )
    assert OutcomeConditionedAdmission(initial).assess(candidate).decision == Decision.WAIT
    assert OutcomeConditionedAdmission(quiescent).assess(candidate).decision == Decision.COMMIT
    alternate = next(
        item
        for item in initial.problem.candidates
        if item.intent.action_name == "alternate_payment"
    )
    assert OutcomeConditionedAdmission(quiescent).assess(alternate).decision == Decision.WAIT


def test_late_commit_is_checked_as_a_real_successor_not_an_absent_receipt() -> None:
    problem = problems()[0]
    alternate = next(
        item for item in problem.candidates if item.intent.action_name == "alternate_payment"
    )
    assert not oracle_safe(problem, alternate, OutcomeSet(values=(ExternalOutcome.IN_FLIGHT,)))
    assert violations(problem, (alternate,), ExternalOutcome.COMMITTED)
    assert not violations(problem, (alternate,), ExternalOutcome.ABSENT)
