"""External-world possibilities are separate from local effect certainty."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExternalOutcome(StrEnum):
    COMMITTED = "COMMITTED"
    ABSENT = "ABSENT"
    IN_FLIGHT = "IN_FLIGHT"


class OutcomeSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    values: tuple[ExternalOutcome, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def canonicalize(self) -> "OutcomeSet":
        if len(set(self.values)) != len(self.values):
            raise ValueError("Possible outcomes must be unique")
        object.__setattr__(self, "values", tuple(sorted(self.values, key=str)))
        return self

    def contains(self, outcome: ExternalOutcome) -> bool:
        return outcome in self.values

    @property
    def terminal(self) -> bool:
        return len(self.values) == 1 and ExternalOutcome.IN_FLIGHT not in self.values


ALL_OUTCOMES = OutcomeSet(values=tuple(ExternalOutcome))
QUIESCENT_OUTCOMES = OutcomeSet(values=(ExternalOutcome.COMMITTED, ExternalOutcome.ABSENT))


def validate_refinement(before: OutcomeSet | None, after: OutcomeSet) -> None:
    if before is not None and not set(after.values) <= set(before.values):
        raise ValueError("Evidence cannot reintroduce an excluded possible outcome")
