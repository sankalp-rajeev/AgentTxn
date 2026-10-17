"""Typed week-one intents, observations, decisions, and audit events."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agenttxn.effects.certainty import Certainty
from agenttxn.effects.outcomes import OutcomeSet


class Operation(StrEnum):
    CHARGE = "charge"
    SHIP = "ship"
    REFUND = "refund"
    CREDIT = "credit"
    CANDIDATE = "candidate"


class Decision(StrEnum):
    COMMIT = "COMMIT"
    WAIT = "WAIT"
    RECONCILE = "RECONCILE"
    COMPENSATE = "COMPENSATE"
    REPLAN = "REPLAN"
    BLOCK = "BLOCK"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class TransactionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    RECONCILING = "RECONCILING"
    COMMITTED = "COMMITTED"
    COMPENSATING = "COMPENSATING"
    ABORTED = "ABORTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class EffectIntent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    effect_id: str = Field(min_length=1)
    logical_operation_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    operation: Operation
    order_id: str | None = None
    incident_id: str | None = None
    amount_cents: int = Field(default=0, ge=0, strict=True)
    resource_footprint: tuple[str, ...] = Field(min_length=1)
    semantic_tags: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    read_versions: dict[str, int] = Field(default_factory=dict)
    action_name: str | None = None

    @model_validator(mode="after")
    def validate_arguments(self) -> "EffectIntent":
        if self.operation in {Operation.CHARGE, Operation.SHIP} and not self.order_id:
            raise ValueError("Charge and shipment require order_id")
        if (
            self.operation in {Operation.CHARGE, Operation.REFUND, Operation.CREDIT}
            and self.amount_cents <= 0
        ):
            raise ValueError("Financial effects require positive integer cents")
        if self.operation in {Operation.REFUND, Operation.CREDIT} and not self.incident_id:
            raise ValueError("Customer compensation requires incident_id")
        return self


class EffectRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    intent: EffectIntent
    certainty: Certainty = Certainty.NOT_STARTED
    possible_outcomes: OutcomeSet | None = None


class Certification(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision: Decision
    reason: str
    invariants: tuple[str, ...] = ()
    blocking_effect_ids: tuple[str, ...] = ()


class LedgerEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    sequence: int
    run_id: str
    transaction_id: str
    agent_id: str
    effect_id: str
    operation: Operation
    event_type: str
    certainty_state_before: Certainty | None = None
    certainty_state_after: Certainty
    decision: Decision | None = None
    reason: str
    relevant_invariants: tuple[str, ...] = ()
    blocking_effect_ids: tuple[str, ...] = ()
    observation: str | None = None
    possible_outcomes: OutcomeSet | None = None
