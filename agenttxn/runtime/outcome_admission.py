"""Gate-1B policy adapter and direct outcome-conditioned admission."""

import hashlib
import json
from abc import ABC, abstractmethod

from agenttxn.effects.ledger import Ledger
from agenttxn.effects.models import Certification, Decision, EffectIntent
from agenttxn.effects.outcomes import ExternalOutcome
from agenttxn.runtime.uncertainty import AdmissionView, Assessment, Candidate, Predicate


def view_hash(view: AdmissionView) -> str:
    canonical = json.dumps(view.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class OutcomeAdmissionPolicy(ABC):
    name: str

    def __init__(self, view: AdmissionView) -> None:
        self.view = view
        self.by_id = {item.intent.effect_id: item for item in view.problem.candidates}

    @abstractmethod
    def assess(self, candidate: Candidate) -> Assessment:
        """Every policy gets the complete identical immutable admission view."""

    def keys(self, intent: EffectIntent) -> tuple[str, ...]:
        return intent.resource_footprint

    async def certify(self, intent: EffectIntent, ledger: Ledger) -> Certification:
        current = await ledger.get(self.view.problem.upstream.effect_id)
        if current.possible_outcomes != self.view.outcomes:
            return Certification(decision=Decision.HUMAN_REVIEW, reason="Stale evidence snapshot")
        result = self.assess(self.by_id[intent.effect_id])
        details = {
            "policy": self.name,
            "input_sha256": view_hash(self.view),
            "evidence_revision": self.view.revision,
            "assessment": result.model_dump(mode="json"),
        }
        return Certification(
            decision=result.decision,
            reason=json.dumps(details, sort_keys=True),
            invariants=tuple(item.invariant_id for item in self.view.problem.invariants),
            blocking_effect_ids=(self.view.problem.upstream.effect_id,)
            if result.decision == Decision.WAIT
            else (),
        )


def holds(predicate: Predicate, state: dict[str, bool]) -> bool:
    """Concrete Boolean interpretation used by OCA, not the symbolic baselines."""
    match predicate.kind:
        case "constant":
            return predicate.value
        case "fact":
            return state[predicate.field] == predicate.value
        case "and":
            return all(holds(child, state) for child in predicate.children)
        case "or":
            return any(holds(child, state) for child in predicate.children)
        case "not":
            return not holds(predicate.children[0], state)
        case "implies":
            return not holds(predicate.children[0], state) or holds(predicate.children[1], state)
    raise ValueError("Unsupported predicate")


class OutcomeConditionedAdmission(OutcomeAdmissionPolicy):
    name = "agenttxn_oca"

    def assess(self, candidate: Candidate) -> Assessment:
        verdicts = []
        for outcome in self.view.outcomes.values:
            continuations = (
                tuple(ExternalOutcome) if outcome == ExternalOutcome.IN_FLIGHT else (outcome,)
            )
            compatible = True
            for continuation in continuations:
                world = next(
                    item for item in self.view.problem.worlds if item.outcome == continuation
                )
                projected = {item.name: item.value for item in world.facts}
                projected.update({item.name: item.value for item in candidate.writes})
                compatible = compatible and all(
                    holds(rule.predicate, projected) for rule in self.view.problem.invariants
                )
            verdicts.append(compatible)
        decision = (
            Decision.COMMIT
            if all(verdicts)
            else (Decision.BLOCK if not any(verdicts) else Decision.WAIT)
        )
        return Assessment(
            decision=decision, reason="Direct universal outcome-conditioned evaluation"
        )
