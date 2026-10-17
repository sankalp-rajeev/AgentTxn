"""Bit-vector joint predicates, independent of the simulation oracle."""

from agenttxn.effects.outcomes import ExternalOutcome
from agenttxn.runtime.uncertainty import Candidate, MatchedProblem, Predicate

OUTCOME_ORDER = tuple(ExternalOutcome)
FULL_MASK = (1 << len(OUTCOME_ORDER)) - 1


def predicate_mask(
    predicate: Predicate,
    problem: MatchedProblem,
    writes: dict[str, bool],
) -> int:
    if predicate.kind == "constant":
        return FULL_MASK if predicate.value else 0
    if predicate.kind == "fact":
        if predicate.field in writes:
            return FULL_MASK if writes[predicate.field] == predicate.value else 0
        mask = 0
        for index, outcome in enumerate(OUTCOME_ORDER):
            world = next(item for item in problem.worlds if item.outcome == outcome)
            value = next(item.value for item in world.facts if item.name == predicate.field)
            if value == predicate.value:
                mask |= 1 << index
        return mask
    masks = [predicate_mask(child, problem, writes) for child in predicate.children]
    if predicate.kind == "not":
        return FULL_MASK ^ masks[0]
    if predicate.kind == "implies":
        return (FULL_MASK ^ masks[0]) | masks[1]
    if predicate.kind == "and":
        result = FULL_MASK
        for mask in masks:
            result &= mask
        return result
    result = 0
    for mask in masks:
        result |= mask
    return result


def temporal_mask(mask: int) -> int:
    """An in-flight world requires compatibility with both possible terminal successors."""
    flight = 1 << OUTCOME_ORDER.index(ExternalOutcome.IN_FLIGHT)
    if mask != FULL_MASK:
        mask &= ~flight
    return mask


def joint_mask(problem: MatchedProblem, action: Candidate) -> int:
    writes = {item.name: item.value for item in action.writes}
    result = FULL_MASK
    for rule in problem.invariants:
        result &= predicate_mask(rule.predicate, problem, writes)
    return temporal_mask(result)


def active_mask(outcomes: tuple[ExternalOutcome, ...]) -> int:
    return sum(1 << OUTCOME_ORDER.index(outcome) for outcome in outcomes)
