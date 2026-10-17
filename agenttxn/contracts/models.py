"""Declared tool capabilities used by the feasibility runtime."""

from pydantic import BaseModel, ConfigDict, Field

from agenttxn.effects.certainty import Certainty
from agenttxn.effects.models import EffectIntent, Operation


class ToolContract(BaseModel):
    model_config = ConfigDict(frozen=True)
    operation: Operation
    idempotency_supported: bool = True
    reconciliation_supported: bool = True
    # A negative probe is definitive only for these immediate, strongly consistent mocks.
    definitive_absence: bool = True
    irreversible: bool = False


def week1_contracts() -> dict[Operation, ToolContract]:
    return {
        operation: ToolContract(operation=operation, irreversible=operation == Operation.SHIP)
        for operation in Operation
    }


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    logical_operation_id: str = Field(min_length=1)
    order_id: str | None = None
    incident_id: str | None = None
    amount_cents: int = Field(default=0, ge=0, strict=True)

    @classmethod
    def from_intent(cls, intent: EffectIntent) -> "ToolRequest":
        return cls(
            logical_operation_id=intent.logical_operation_id,
            order_id=intent.order_id,
            incident_id=intent.incident_id,
            amount_cents=intent.amount_cents,
        )


class ToolOutcome(BaseModel):
    certainty: Certainty
    receipt_id: str | None = None
    reason: str
