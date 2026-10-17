"""Independent possible-world simulation and finite joint-safety checks."""

from itertools import combinations

from agenttxn.effects.outcomes import ExternalOutcome, OutcomeSet
from agenttxn.runtime.uncertainty import Candidate, MatchedProblem, Predicate


def evaluate_predicate(predicate: Predicate, state: dict[str, bool]) -> bool:
    if predicate.kind == "constant":
        return predicate.value
    if predicate.kind == "fact":
        return state[predicate.field] == predicate.value
    values = [evaluate_predicate(child, state) for child in predicate.children]
    if predicate.kind == "and":
        return all(values)
    if predicate.kind == "or":
        return any(values)
    if predicate.kind == "not":
        return not values[0]
    return not values[0] or values[1]


def successors(outcome: ExternalOutcome) -> tuple[ExternalOutcome, ...]:
    if outcome == ExternalOutcome.IN_FLIGHT:
        return (outcome, ExternalOutcome.COMMITTED, ExternalOutcome.ABSENT)
    return (outcome,)


def violations(
    problem: MatchedProblem,
    actions: tuple[Candidate, ...],
    outcome: ExternalOutcome,
) -> tuple[str, ...]:
    binding = next(world for world in problem.worlds if world.outcome == outcome)
    state = {item.name: item.value for item in binding.facts}
    for action in actions:
        state.update({item.name: item.value for item in action.writes})
    return tuple(
        rule.invariant_id
        for rule in problem.invariants
        if not evaluate_predicate(rule.predicate, state)
    )


def oracle_safe(problem: MatchedProblem, action: Candidate, outcomes: OutcomeSet) -> bool:
    return all(
        not violations(problem, (action,), later)
        for outcome in outcomes.values
        for later in successors(outcome)
    )


def safe_outcomes(problem: MatchedProblem, action: Candidate) -> tuple[ExternalOutcome, ...]:
    return tuple(
        outcome
        for outcome in ExternalOutcome
        if oracle_safe(problem, action, OutcomeSet(values=(outcome,)))
    )


def joint_subset_audit(problem: MatchedProblem, outcomes: OutcomeSet) -> int:
    """Enumerate every subset of individually safe effects, including the empty set."""
    eligible = tuple(
        action for action in problem.candidates if oracle_safe(problem, action, outcomes)
    )
    checked = 0
    for size in range(len(eligible) + 1):
        for subset in combinations(eligible, size):
            for outcome in outcomes.values:
                for later in successors(outcome):
                    if violations(problem, subset, later):
                        raise ValueError(
                            "Individually safe candidates have a joint invariant conflict"
                        )
            checked += 1
    return checked
