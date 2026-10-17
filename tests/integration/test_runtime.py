import asyncio

import pytest

from agenttxn.contracts.models import week1_contracts
from agenttxn.effects.certainty import Certainty
from agenttxn.effects.ledger import MemoryLedger
from agenttxn.effects.models import Certification, Decision, EffectIntent, Operation
from agenttxn.faults.injector import Fault
from agenttxn.runtime.certifier import SemanticCertifier
from agenttxn.runtime.coordinator import Coordinator
from baselines.naive import NaivePolicy
from baselines.resource_occ import ResourceOCC
from services.common import ConcurrencyProbe, ToolRequest
from txnagentbench.local import local_services

pytestmark = pytest.mark.integration


def action(
    operation: Operation, effect_id: str, *, incident: str = "incident", amount: int = 30000
) -> EffectIntent:
    return EffectIntent(
        effect_id=effect_id,
        logical_operation_id=effect_id,
        transaction_id=f"txn:{effect_id}",
        agent_id=effect_id,
        workflow_id=effect_id,
        operation=operation,
        order_id="order",
        incident_id=incident if operation in {Operation.REFUND, Operation.CREDIT} else None,
        amount_cents=amount if operation != Operation.SHIP else 0,
        resource_footprint=(f"{operation}:{effect_id}",),
    )


@pytest.mark.parametrize("fault", [Fault.TIMEOUT_BEFORE_EFFECT, Fault.TIMEOUT_AFTER_EFFECT])
async def test_identical_timeouts_are_resolved_with_provider_evidence(fault: Fault) -> None:
    ledger = MemoryLedger("test")
    async with local_services({"charge": fault}) as (adapter, providers):
        runtime = Coordinator(ledger, adapter, SemanticCertifier({}))
        await runtime.submit(action(Operation.CHARGE, "charge"))
        assert (await ledger.get("charge")).certainty == Certainty.UNKNOWN
        result = await runtime.submit(action(Operation.SHIP, "ship"))
        if fault == Fault.TIMEOUT_AFTER_EFFECT:
            assert result.decision == Decision.COMMIT
            assert len(providers[Operation.SHIP].effects) == 1
        else:
            assert result.decision == Decision.BLOCK
            assert not providers[Operation.SHIP].effects
        assert len(providers[Operation.CHARGE].effects) == (fault == Fault.TIMEOUT_AFTER_EFFECT)
        assert providers[Operation.CHARGE].faults.attempts["charge"] == 1


async def test_unknown_reservation_counts_and_does_not_block_another_incident() -> None:
    ledger = MemoryLedger("test")
    async with local_services({"refund": Fault.TIMEOUT_AFTER_EFFECT}) as (adapter, providers):
        runtime = Coordinator(
            ledger, adapter, SemanticCertifier({"incident": 50000, "other": 50000})
        )
        await runtime.submit(action(Operation.REFUND, "refund"))
        assert (await ledger.get("refund")).certainty == Certainty.UNKNOWN
        assert (await runtime.submit(action(Operation.CREDIT, "credit"))).decision == Decision.BLOCK
        independent = await runtime.submit(
            action(Operation.CREDIT, "independent", incident="other")
        )
        assert independent.decision == Decision.COMMIT
        assert len(providers[Operation.CREDIT].effects) == 1


async def test_unreconcilable_prerequisite_escalates_without_guessing_or_retrying() -> None:
    ledger = MemoryLedger("test")
    contracts = week1_contracts()
    contracts[Operation.CHARGE] = contracts[Operation.CHARGE].model_copy(
        update={"reconciliation_supported": False}
    )
    async with local_services({"charge": Fault.TIMEOUT_AFTER_EFFECT}, contracts=contracts) as (
        adapter,
        providers,
    ):
        runtime = Coordinator(ledger, adapter, SemanticCertifier({}))
        await runtime.submit(action(Operation.CHARGE, "charge"))
        result = await runtime.submit(action(Operation.SHIP, "ship"))
        assert result.decision == Decision.HUMAN_REVIEW
        assert (await ledger.get("charge")).certainty == Certainty.UNKNOWN
        assert not providers[Operation.SHIP].effects
        await runtime.submit(action(Operation.CHARGE, "charge"))
        assert providers[Operation.CHARGE].faults.attempts["charge"] == 1


async def test_negative_read_without_absence_guarantee_preserves_unknown() -> None:
    contracts = week1_contracts()
    contracts[Operation.CHARGE] = contracts[Operation.CHARGE].model_copy(
        update={"definitive_absence": False}
    )
    async with local_services({"charge": Fault.TIMEOUT_BEFORE_EFFECT}, contracts=contracts) as (
        adapter,
        providers,
    ):
        ledger = MemoryLedger("test")
        runtime = Coordinator(ledger, adapter, SemanticCertifier({}))
        await runtime.submit(action(Operation.CHARGE, "charge"))
        result = await runtime.submit(action(Operation.SHIP, "ship"))
        assert result.decision == Decision.HUMAN_REVIEW
        assert (await ledger.get("charge")).certainty == Certainty.UNKNOWN
        assert not providers[Operation.SHIP].effects


async def test_waiting_shipment_wakes_after_payment_without_polling() -> None:
    waiting = asyncio.Event()

    class ObservingLedger(MemoryLedger):
        async def decide(self, effect_id: str, result: Certification) -> None:
            await super().decide(effect_id, result)
            if result.decision == Decision.WAIT:
                waiting.set()

    probe = ConcurrencyProbe(require_overlap=99)
    async with local_services(probe=probe) as (adapter, providers):
        ledger = ObservingLedger("test")
        runtime = Coordinator(ledger, adapter, SemanticCertifier({}))
        payment = asyncio.create_task(runtime.submit(action(Operation.CHARGE, "charge")))
        await asyncio.wait_for(probe.ready.wait(), 2)
        shipment = asyncio.create_task(runtime.submit(action(Operation.SHIP, "ship")))
        await asyncio.wait_for(waiting.wait(), 2)
        probe.release.set()
        await asyncio.wait_for(asyncio.gather(payment, shipment), 2)
        assert len(providers[Operation.SHIP].effects) == 1
        assert (await ledger.get("charge")).certainty == Certainty.CONFIRMED


async def test_pending_budget_reservation_prevents_a_second_external_dispatch() -> None:
    probe = ConcurrencyProbe(require_overlap=99)
    async with local_services(probe=probe) as (adapter, providers):
        ledger = MemoryLedger("test")
        runtime = Coordinator(ledger, adapter, SemanticCertifier({"incident": 50000}))
        first = asyncio.create_task(runtime.submit(action(Operation.REFUND, "refund")))
        await asyncio.wait_for(probe.ready.wait(), 2)
        try:
            second = await runtime.submit(action(Operation.CREDIT, "credit"))
            assert second.decision == Decision.BLOCK
            assert (await ledger.get("refund")).certainty == Certainty.PENDING
            assert not providers[Operation.CREDIT].effects
        finally:
            probe.release.set()
            await first


async def test_independent_provider_calls_actually_overlap() -> None:
    probe = ConcurrencyProbe(require_overlap=2)
    async with local_services(probe=probe) as (adapter, _):
        runtime = Coordinator(
            MemoryLedger("test"), adapter, SemanticCertifier({"incident": 50000, "other": 50000})
        )
        results = await asyncio.wait_for(
            asyncio.gather(
                runtime.submit(action(Operation.REFUND, "refund")),
                runtime.submit(action(Operation.CREDIT, "credit", incident="other")),
            ),
            2,
        )
        assert all(result.decision == Decision.COMMIT for result in results)
        assert probe.max_in_flight == 2


@pytest.mark.parametrize("policy_name", ["naive", "resource_occ", "semantic_scope", "agenttxn"])
async def test_disjoint_resource_race_and_augmented_occ_control(policy_name: str) -> None:
    policy = {
        "naive": NaivePolicy(),
        "resource_occ": ResourceOCC(),
        "semantic_scope": ResourceOCC(semantic_scopes=True),
        "agenttxn": SemanticCertifier({"incident": 50000}),
    }[policy_name]
    async with local_services() as (adapter, providers):
        runtime = Coordinator(MemoryLedger("test"), adapter, policy)
        await asyncio.gather(
            runtime.submit(action(Operation.REFUND, "refund")),
            runtime.submit(action(Operation.CREDIT, "credit")),
        )
        total = sum(
            effect.request.amount_cents
            for provider in providers.values()
            for effect in provider.effects.values()
        )
        assert total == (60000 if policy_name in {"naive", "resource_occ"} else 30000)


async def test_provider_deduplicates_concurrent_identical_keys() -> None:
    probe = ConcurrencyProbe(require_overlap=2)
    async with local_services(probe=probe) as (_, providers):
        provider = providers[Operation.CHARGE]
        request = ToolRequest(logical_operation_id="same", order_id="order", amount_cents=100)
        outcomes = await asyncio.gather(provider.execute(request), provider.execute(request))
        assert outcomes[0].receipt_id == outcomes[1].receipt_id
        assert len(provider.effects) == 1
