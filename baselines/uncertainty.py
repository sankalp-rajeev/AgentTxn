"""Strong matched-information admission models, not full research-system ports."""

from dataclasses import dataclass

from agenttxn.effects.models import Decision
from agenttxn.effects.outcomes import ExternalOutcome
from agenttxn.invariants.symbolic import (
    OUTCOME_ORDER,
    active_mask,
    joint_mask,
    predicate_mask,
    temporal_mask,
)
from agenttxn.runtime.outcome_admission import OutcomeAdmissionPolicy, OutcomeConditionedAdmission
from agenttxn.runtime.uncertainty import AdmissionView, Assessment, Candidate, MatchedProblem


def mask_decision(allowed: int, active: int) -> Decision:
    compatible = allowed & active
    if compatible == active:
        return Decision.COMMIT
    return Decision.BLOCK if compatible == 0 else Decision.WAIT


class GlobalFailClosed(OutcomeAdmissionPolicy):
    name = "global_fail_closed"

    def assess(self, candidate: Candidate) -> Assessment:
        decision = mask_decision(
            joint_mask(self.view.problem, candidate), active_mask(self.view.outcomes.values)
        )
        if decision != Decision.BLOCK and not self.view.outcomes.terminal:
            decision = Decision.WAIT
        return Assessment(decision=decision, reason="Global unresolved-effect barrier")


@dataclass(frozen=True)
class ConflictScope:
    key: str
    outcome: ExternalOutcome


def compile_scopes(problem: MatchedProblem, candidate: Candidate) -> tuple[ConflictScope, ...]:
    """Finite predicate locks from supplied invariant definitions, not oracle labels."""
    result = []
    writes = {item.name: item.value for item in candidate.writes}
    for rule in problem.invariants:
        compatible = temporal_mask(predicate_mask(rule.predicate, problem, writes))
        for index, outcome in enumerate(OUTCOME_ORDER):
            if not compatible & (1 << index):
                result.append(
                    ConflictScope(
                        key=f"{problem.upstream.effect_id}:{rule.invariant_id}:{outcome}",
                        outcome=outcome,
                    )
                )
    return tuple(result)


class SyntheticScopeOCC(OutcomeAdmissionPolicy):
    name = "synthetic_scope_occ"

    def __init__(self, view: AdmissionView) -> None:
        super().__init__(view)
        self.plans = {
            item.intent.effect_id: compile_scopes(view.problem, item)
            for item in view.problem.candidates
        }

    def assess(self, candidate: Candidate) -> Assessment:
        plan = self.plans[candidate.intent.effect_id]
        # Excluded outcomes have quiescent version slots. Still-possible conflicting
        # outcomes remain reserved; the common adapter checks evidence revision.
        blocked = tuple(scope.key for scope in plan if scope.outcome in self.view.outcomes.values)
        conflicting = {scope.outcome for scope in plan if scope.key in blocked}
        decision = (
            Decision.COMMIT
            if not blocked
            else (
                Decision.BLOCK if conflicting == set(self.view.outcomes.values) else Decision.WAIT
            )
        )
        return Assessment(
            decision=decision,
            reason="Validate complete synthetic predicate-scope reservations",
            coordination_scopes=tuple(scope.key for scope in plan),
            blocked_scopes=blocked,
        )


class AtomixScopeFrontier(SyntheticScopeOCC):
    name = "atomix_scope_frontier"

    def assess(self, candidate: Candidate) -> Assessment:
        plan = self.plans[candidate.intent.effect_id]
        candidate_epoch = 1
        # U at epoch zero holds only still-possible incompatible outcome scopes.
        frontiers = {
            scope.key: (0 if scope.outcome in self.view.outcomes.values else candidate_epoch)
            for scope in plan
        }
        blocked = tuple(scope.key for scope in plan if frontiers[scope.key] < candidate_epoch)
        conflicting = {scope.outcome for scope in plan if scope.key in blocked}
        decision = (
            Decision.COMMIT
            if not blocked
            else (
                Decision.BLOCK if conflicting == set(self.view.outcomes.values) else Decision.WAIT
            )
        )
        return Assessment(
            decision=decision,
            reason="Sealed complete scopes; check local progress frontiers",
            coordination_scopes=tuple(scope.key for scope in plan),
            blocked_scopes=blocked,
        )


class SemanticPendingLock(OutcomeAdmissionPolicy):
    name = "semantic_pending_lock"

    def __init__(self, view: AdmissionView) -> None:
        super().__init__(view)
        # Compatibility modes are derived from the same executable business rules.
        self.incompatible = {
            item.intent.effect_id: frozenset(
                scope.outcome for scope in compile_scopes(view.problem, item)
            )
            for item in view.problem.candidates
        }

    def assess(self, candidate: Candidate) -> Assessment:
        modes = self.incompatible[candidate.intent.effect_id]
        held = set(self.view.outcomes.values)
        incompatible = held & modes
        decision = (
            Decision.COMMIT
            if not incompatible
            else (Decision.BLOCK if incompatible == held else Decision.WAIT)
        )
        return Assessment(
            decision=decision, reason="Semantic pending-state lock compatibility matrix"
        )


class TCTJointRecertification(OutcomeAdmissionPolicy):
    name = "tct_c_joint_recertification"

    def assess(self, candidate: Candidate) -> Assessment:
        # A complete joint current vector, including outcome possibility and temporal
        # continuation, is evaluated symbolically. No per-token approval shortcut.
        allowed = joint_mask(self.view.problem, candidate)
        decision = mask_decision(allowed, active_mask(self.view.outcomes.values))
        return Assessment(
            decision=decision, reason="Complete jointly protected current-vector predicate"
        )


POLICIES: tuple[type[OutcomeAdmissionPolicy], ...] = (
    GlobalFailClosed,
    SyntheticScopeOCC,
    AtomixScopeFrontier,
    SemanticPendingLock,
    TCTJointRecertification,
    OutcomeConditionedAdmission,
)
