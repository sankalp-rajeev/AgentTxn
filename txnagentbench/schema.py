"""Validated week-one scenarios, including the complete PRD scenario contract."""

from pydantic import BaseModel, ConfigDict, JsonValue

from agenttxn.contracts.models import ToolContract
from agenttxn.effects.models import EffectIntent
from agenttxn.faults.injector import Fault


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    scenario_id: str
    domain: str
    initial_state: dict[str, JsonValue]
    agents: tuple[str, ...]
    workflows: tuple[EffectIntent, ...]
    tool_contracts: tuple[ToolContract, ...]
    semantic_invariants: tuple[str, ...]
    fault_schedule: dict[str, Fault]
    success_conditions: tuple[str, ...]
    forbidden_states: tuple[str, ...]
    expected_serial_outcome: str
    budgets_cents: dict[str, int]
    require_provider_overlap: int = 0
