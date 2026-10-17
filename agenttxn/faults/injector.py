"""Deterministic per-logical-operation faults; no wall-clock randomness."""

from enum import StrEnum


class Fault(StrEnum):
    NONE = "none"
    TIMEOUT_BEFORE_EFFECT = "timeout_before_effect"
    TIMEOUT_AFTER_EFFECT = "timeout_after_effect"
    LATE_COMMIT = "late_commit"
    RECONCILIATION_UNAVAILABLE = "reconciliation_unavailable"


class FaultInjector:
    def __init__(self, schedule: dict[str, Fault] | None = None) -> None:
        self.schedule = dict(schedule or {})
        self.attempts: dict[str, int] = {}

    def on_execute(self, logical_operation_id: str) -> Fault:
        attempt = self.attempts.get(logical_operation_id, 0) + 1
        self.attempts[logical_operation_id] = attempt
        # Submission faults occur exactly once; reconciliation faults persist.
        fault = self.schedule.get(logical_operation_id, Fault.NONE)
        return fault if attempt == 1 else Fault.NONE

    def on_probe(self, logical_operation_id: str) -> Fault:
        fault = self.schedule.get(logical_operation_id, Fault.NONE)
        return fault if fault == Fault.RECONCILIATION_UNAVAILABLE else Fault.NONE
