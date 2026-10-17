"""Immutable matched inputs and a small declarative invariant language for Gate 1B."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agenttxn.contracts.models import ToolContract
from agenttxn.effects.models import Decision, EffectIntent
from agenttxn.effects.outcomes import ExternalOutcome, OutcomeSet


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Fact(FrozenModel):
    name: str
    value: bool


class Predicate(FrozenModel):
    kind: Literal["fact", "and", "or", "not", "implies", "constant"]
    field: str = ""
    value: bool = True
    children: tuple["Predicate", ...] = ()

    @model_validator(mode="after")
    def check_arity(self) -> "Predicate":
        if self.kind == "fact" and not self.field:
            raise ValueError("A fact predicate needs a field")
        expected = {"not": 1, "implies": 2}
        if self.kind in expected and len(self.children) != expected[self.kind]:
            raise ValueError("Invalid predicate arity")
        if self.kind in {"and", "or"} and not self.children:
            raise ValueError("Empty Boolean connective is forbidden")
        return self


class Invariant(FrozenModel):
    invariant_id: str
    predicate: Predicate


class OutcomeWorld(FrozenModel):
    outcome: ExternalOutcome
    facts: tuple[Fact, ...]


class Candidate(FrozenModel):
    intent: EffectIntent
    writes: tuple[Fact, ...] = Field(min_length=1)
    reads: tuple[str, ...]
    coarse_context: str
    contract: ToolContract

    @model_validator(mode="after")
    def unique_writes(self) -> "Candidate":
        if len({fact.name for fact in self.writes}) != len(self.writes):
            raise ValueError("Candidate writes must name distinct facts")
        return self


class Observation(FrozenModel):
    round: int
    description: str
    outcomes: OutcomeSet


class MatchedProblem(FrozenModel):
    scenario_id: str
    upstream: EffectIntent
    upstream_contract: ToolContract
    worlds: tuple[OutcomeWorld, ...]
    invariants: tuple[Invariant, ...]
    candidates: tuple[Candidate, ...]
    # Public schedule has no hidden realization or future receipt value.
    fault_schedule: tuple[str, ...]
    reconciliation_endpoint: str
    causal_contract: str
    version: str = "gate1b-v1"

    @model_validator(mode="after")
    def check_complete(self) -> "MatchedProblem":
        if {world.outcome for world in self.worlds} != set(ExternalOutcome):
            raise ValueError("Exactly the three external outcome worlds are required")
        if len(self.worlds) != 3:
            raise ValueError("World bindings must be unique")
        if len({item.intent.effect_id for item in self.candidates}) != len(self.candidates):
            raise ValueError("Candidate effect identities must be unique")
        fields = {fact.name for fact in self.worlds[0].facts}
        if any({fact.name for fact in world.facts} != fields for world in self.worlds):
            raise ValueError("Every world must provide the same complete dependency vector")
        writes = {fact.name for candidate in self.candidates for fact in candidate.writes}
        if not writes <= fields:
            raise ValueError("Candidate writes must belong to the declared dependency vector")
        return self


class AdmissionView(FrozenModel):
    problem: MatchedProblem
    observations: tuple[Observation, ...] = Field(min_length=1)

    @property
    def outcomes(self) -> OutcomeSet:
        return self.observations[-1].outcomes

    @property
    def revision(self) -> int:
        return self.observations[-1].round


class Assessment(FrozenModel):
    decision: Decision
    reason: str
    coordination_scopes: tuple[str, ...] = ()
    blocked_scopes: tuple[str, ...] = ()


def fact(name: str, value: bool = True) -> Predicate:
    return Predicate(kind="fact", field=name, value=value)


def all_of(*children: Predicate) -> Predicate:
    return Predicate(kind="and", children=children)


def implies(antecedent: Predicate, consequent: Predicate) -> Predicate:
    return Predicate(kind="implies", children=(antecedent, consequent))
