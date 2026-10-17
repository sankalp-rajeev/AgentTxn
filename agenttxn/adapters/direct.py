"""HTTP tool adapter with explicit ambiguous outcomes and contract checks."""

from urllib.parse import quote

import httpx

from agenttxn.contracts.models import ToolContract, ToolOutcome, ToolRequest
from agenttxn.effects.certainty import Certainty
from agenttxn.effects.models import EffectIntent, Operation
from agenttxn.effects.outcomes import ALL_OUTCOMES, ExternalOutcome


class DirectAdapter:
    def __init__(
        self,
        clients: dict[Operation, httpx.AsyncClient],
        contracts: dict[Operation, ToolContract],
    ) -> None:
        self.clients = clients
        self.contracts = contracts

    async def execute(self, intent: EffectIntent) -> ToolOutcome:
        try:
            response = await self.clients[intent.operation].post(
                "/effects",
                json=ToolRequest.from_intent(intent).model_dump(mode="json"),
            )
            if response.status_code >= 500:
                return ToolOutcome(
                    certainty=Certainty.UNKNOWN, reason="Ambiguous provider response"
                )
            if 400 <= response.status_code < 500:
                return ToolOutcome(certainty=Certainty.FAILED, reason="Provider rejected request")
            response.raise_for_status()
            outcome = ToolOutcome.model_validate(response.json())
            if outcome.certainty not in {Certainty.CONFIRMED, Certainty.FAILED, Certainty.UNKNOWN}:
                return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Invalid provider outcome")
            return outcome
        except (httpx.TransportError, ValueError):
            return ToolOutcome(
                certainty=Certainty.UNKNOWN, reason="Unresolved transport or response"
            )

    async def reconcile(self, intent: EffectIntent) -> ToolOutcome:
        contract = self.contracts[intent.operation]
        if not contract.reconciliation_supported:
            return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Contract has no reconciliation")
        try:
            response = await self.clients[intent.operation].get(
                f"/operations/{quote(intent.logical_operation_id, safe='')}"
            )
            if response.status_code != 200:
                return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Reconciliation unavailable")
            outcome = ToolOutcome.model_validate(response.json())
            if outcome.certainty == Certainty.FAILED and not contract.definitive_absence:
                return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Absence is not definitive")
            if (
                outcome.certainty == Certainty.UNKNOWN
                and outcome.possible_outcomes is not None
                and not outcome.possible_outcomes.contains(ExternalOutcome.IN_FLIGHT)
                and not contract.quiescence_certificate_supported
            ):
                return ToolOutcome(
                    certainty=Certainty.UNKNOWN,
                    reason="Contract cannot exclude in-flight writes",
                    possible_outcomes=ALL_OUTCOMES,
                )
            if outcome.certainty not in {Certainty.CONFIRMED, Certainty.FAILED, Certainty.UNKNOWN}:
                return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Invalid probe outcome")
            return outcome
        except (httpx.TransportError, ValueError):
            return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Unresolved probe")
