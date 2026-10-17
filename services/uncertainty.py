"""Opaque-receipt schedules atop the Week-1 provider, with explicit late completion."""

from enum import StrEnum

from agenttxn.contracts.models import ToolOutcome
from agenttxn.effects.certainty import Certainty
from agenttxn.effects.models import Operation
from agenttxn.effects.outcomes import ALL_OUTCOMES, QUIESCENT_OUTCOMES, ExternalOutcome, OutcomeSet
from agenttxn.faults.injector import Fault, FaultInjector
from services.common import MockProvider, ProviderEffect


class Realization(StrEnum):
    HIDDEN_COMMITTED = "hidden_committed"
    HIDDEN_ABSENT = "hidden_absent"
    LATE_COMMIT = "late_commit"
    TERMINAL_ABORT = "terminal_abort"


class ScheduledUncertainProvider(MockProvider):
    def __init__(
        self,
        operation: Operation,
        realization: Realization,
        journal: list[ProviderEffect],
    ) -> None:
        fault = {
            Realization.HIDDEN_COMMITTED: Fault.TIMEOUT_AFTER_EFFECT,
            Realization.HIDDEN_ABSENT: Fault.TIMEOUT_BEFORE_EFFECT,
            Realization.LATE_COMMIT: Fault.LATE_COMMIT,
            Realization.TERMINAL_ABORT: Fault.LATE_COMMIT,
        }[realization]
        super().__init__(operation, FaultInjector({"upstream": fault}), journal=journal)
        self.realization = realization
        self.round = 0

    @property
    def real_outcome(self) -> ExternalOutcome:
        if "upstream" in self.effects:
            return ExternalOutcome.COMMITTED
        if "upstream" in self.pending:
            return ExternalOutcome.IN_FLIGHT
        return ExternalOutcome.ABSENT

    def advance(self, round_number: int) -> None:
        if round_number != self.round + 1:
            raise ValueError("Evidence rounds must advance one step at a time")
        if round_number == 2:
            if "upstream" in self.pending:
                self.settle_pending("upstream", commit=self.realization == Realization.LATE_COMMIT)
            elif "upstream" not in self.effects:
                self.terminal_absent.add("upstream")
        self.round = round_number

    def reconcile(self, logical_operation_id: str) -> ToolOutcome:
        if logical_operation_id != "upstream":
            return super().reconcile(logical_operation_id)
        if self.round < 2:
            return ToolOutcome(
                certainty=Certainty.UNKNOWN,
                reason="Opaque unresolved receipt lookup",
                possible_outcomes=ALL_OUTCOMES,
            )
        if self.round == 2:
            return ToolOutcome(
                certainty=Certainty.UNKNOWN,
                reason="Authoritative no-in-flight certificate; receipt still hidden",
                possible_outcomes=QUIESCENT_OUTCOMES,
            )
        if self.real_outcome == ExternalOutcome.COMMITTED:
            return ToolOutcome(
                certainty=Certainty.CONFIRMED,
                receipt_id=self.effects["upstream"].receipt_id,
                reason="Authoritative committed receipt",
                possible_outcomes=OutcomeSet(values=(ExternalOutcome.COMMITTED,)),
            )
        if "upstream" not in self.terminal_absent:
            raise ValueError("Definitive absence requires a terminal-abort fence")
        return ToolOutcome(
            certainty=Certainty.FAILED,
            reason="Authoritative terminal-abort receipt",
            possible_outcomes=OutcomeSet(values=(ExternalOutcome.ABSENT,)),
        )
