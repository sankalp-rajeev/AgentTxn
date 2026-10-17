"""Mock provider truth and HTTP endpoints, separate from runtime observations."""

import asyncio
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agenttxn.contracts.models import ToolOutcome, ToolRequest
from agenttxn.effects.certainty import Certainty
from agenttxn.effects.models import Operation
from agenttxn.faults.injector import Fault, FaultInjector


class ProviderEffect(BaseModel):
    operation: Operation
    request: ToolRequest
    receipt_id: str


@dataclass
class ConcurrencyProbe:
    """A rendezvous proves overlap without treating latency noise as throughput."""

    require_overlap: int = 0
    hold_until_release: bool = False
    running: int = 0
    max_in_flight: int = 0
    entered: int = 0
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)

    async def enter(self) -> None:
        self.running += 1
        self.entered += 1
        self.max_in_flight = max(self.max_in_flight, self.running)
        self.ready.set()
        if self.require_overlap or self.hold_until_release:
            if self.require_overlap and self.running >= self.require_overlap:
                self.release.set()
            await asyncio.wait_for(self.release.wait(), timeout=10)

    def leave(self) -> None:
        self.running -= 1


class MockProvider:
    def __init__(
        self,
        operation: Operation,
        faults: FaultInjector | None = None,
        probe: ConcurrencyProbe | None = None,
        journal: list[ProviderEffect] | None = None,
    ) -> None:
        self.operation = operation
        self.faults = faults or FaultInjector()
        self.probe = probe or ConcurrencyProbe()
        self.effects: dict[str, ProviderEffect] = {}
        self.journal = journal if journal is not None else []
        self.pending: dict[str, ToolRequest] = {}
        self.terminal_absent: set[str] = set()

    async def execute(self, request: ToolRequest) -> ToolOutcome:
        if self.operation in {Operation.CHARGE, Operation.SHIP} and not request.order_id:
            raise HTTPException(422, "order_id is required")
        if (
            self.operation in {Operation.CHARGE, Operation.REFUND, Operation.CREDIT}
            and request.amount_cents <= 0
        ):
            raise HTTPException(422, "Positive integer cents required")
        if self.operation in {Operation.REFUND, Operation.CREDIT} and not request.incident_id:
            raise HTTPException(422, "incident_id is required")
        existing = self.effects.get(request.logical_operation_id)
        if existing:
            if existing.request != request:
                raise HTTPException(409, "Idempotency key reused with different arguments")
            return ToolOutcome(
                certainty=Certainty.CONFIRMED,
                receipt_id=existing.receipt_id,
                reason="Existing idempotent receipt",
            )
        if request.logical_operation_id in self.pending:
            if self.pending[request.logical_operation_id] != request:
                raise HTTPException(409, "Idempotency key reused with different arguments")
            return ToolOutcome(
                certainty=Certainty.UNKNOWN, reason="Same idempotent request in flight"
            )
        if request.logical_operation_id in self.terminal_absent:
            return ToolOutcome(certainty=Certainty.FAILED, reason="Authoritative terminal abort")
        fault = self.faults.on_execute(request.logical_operation_id)
        if fault == Fault.LATE_COMMIT:
            self.pending[request.logical_operation_id] = request.model_copy(deep=True)
            raise HTTPException(504, "Ambiguous timeout")
        if fault == Fault.TIMEOUT_BEFORE_EFFECT:
            raise HTTPException(504, "Ambiguous timeout")
        try:
            await self.probe.enter()
            # Re-check after yielding: concurrent duplicate requests share one receipt.
            existing = self.effects.get(request.logical_operation_id)
            if existing and existing.request != request:
                raise HTTPException(409, "Idempotency key reused with different arguments")
            effect = existing or ProviderEffect(
                operation=self.operation,
                request=request.model_copy(deep=True),
                receipt_id=f"{self.operation}:{request.logical_operation_id}",
            )
            self.effects[request.logical_operation_id] = effect
            if existing is None:
                self.journal.append(effect.model_copy(deep=True))
        finally:
            self.probe.leave()
        if fault == Fault.TIMEOUT_AFTER_EFFECT:
            raise HTTPException(504, "Ambiguous timeout")
        return ToolOutcome(
            certainty=Certainty.CONFIRMED, receipt_id=effect.receipt_id, reason="Provider committed"
        )

    def reconcile(self, logical_operation_id: str) -> ToolOutcome:
        if logical_operation_id in self.pending:
            return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Request remains in flight")
        if self.faults.on_probe(logical_operation_id) == Fault.RECONCILIATION_UNAVAILABLE:
            return ToolOutcome(certainty=Certainty.UNKNOWN, reason="Probe unavailable")
        effect = self.effects.get(logical_operation_id)
        if effect:
            return ToolOutcome(
                certainty=Certainty.CONFIRMED,
                receipt_id=effect.receipt_id,
                reason="Authoritative provider receipt",
            )
        return ToolOutcome(
            certainty=Certainty.FAILED,
            reason="Definitively absent: immediate provider has no in-flight writes",
        )

    def settle_pending(self, logical_operation_id: str, *, commit: bool) -> None:
        request = self.pending.pop(logical_operation_id)
        if commit:
            effect = ProviderEffect(
                operation=self.operation,
                request=request,
                receipt_id=f"{self.operation}:{logical_operation_id}",
            )
            self.effects[logical_operation_id] = effect
            self.journal.append(effect.model_copy(deep=True))
        else:
            self.terminal_absent.add(logical_operation_id)


def create_app(provider: MockProvider) -> FastAPI:
    app = FastAPI(title=f"AgentTxn mock {provider.operation}")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/effects", response_model=ToolOutcome)
    async def execute(request: ToolRequest) -> ToolOutcome:
        return await provider.execute(request)

    @app.get("/operations/{logical_operation_id}", response_model=ToolOutcome)
    async def reconcile(logical_operation_id: str) -> ToolOutcome:
        return provider.reconcile(logical_operation_id)

    return app
