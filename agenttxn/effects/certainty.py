"""Evidence-based certainty states for external effects."""

from enum import StrEnum


class Certainty(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    COMPENSATED = "COMPENSATED"


TRANSITIONS: dict[Certainty, frozenset[Certainty]] = {
    Certainty.NOT_STARTED: frozenset({Certainty.PENDING}),
    Certainty.PENDING: frozenset({Certainty.CONFIRMED, Certainty.FAILED, Certainty.UNKNOWN}),
    Certainty.UNKNOWN: frozenset({Certainty.CONFIRMED, Certainty.FAILED}),
    Certainty.CONFIRMED: frozenset({Certainty.COMPENSATED}),
    Certainty.FAILED: frozenset(),
    Certainty.COMPENSATED: frozenset(),
}


def validate_transition(before: Certainty, after: Certainty) -> None:
    if after not in TRANSITIONS[before]:
        raise ValueError(f"Invalid certainty transition: {before} -> {after}")
