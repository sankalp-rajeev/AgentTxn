"""Run identical scenarios with deterministic dispatch scheduling and trace exports."""

import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from agenttxn.effects.ledger import Ledger, MemoryLedger
from agenttxn.effects.models import EffectIntent, LedgerEvent, Operation
from agenttxn.effects.postgres import PostgresLedger
from agenttxn.runtime.certifier import SemanticCertifier
from agenttxn.runtime.coordinator import AdmissionPolicy, Coordinator
from baselines.naive import NaivePolicy
from baselines.resource_occ import ResourceOCC
from services.common import ConcurrencyProbe, ProviderEffect
from txnagentbench.evaluator import Metrics, evaluate
from txnagentbench.local import local_services
from txnagentbench.schema import Scenario

BASELINES = ("naive", "resource_occ", "agenttxn", "resource_occ_semantic_scope")


class RunResult(BaseModel):
    scenario_id: str
    baseline: str
    seed: int
    scenario_sha256: str
    metrics: Metrics
    trace_file: str


def policy_for(name: str, scenario: Scenario) -> AdmissionPolicy:
    if name == "naive":
        return NaivePolicy()
    if name == "resource_occ":
        return ResourceOCC()
    if name == "resource_occ_semantic_scope":
        return ResourceOCC(semantic_scopes=True)
    if name == "agenttxn":
        return SemanticCertifier(scenario.budgets_cents)
    raise ValueError(f"Unknown baseline: {name}")


def scenario_hash(scenario: Scenario) -> str:
    canonical = json.dumps(scenario.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def run_scenario(
    scenario: Scenario,
    baseline: str,
    seed: int,
    output: Path,
    database_url: str | None = None,
) -> RunResult:
    # A unique storage namespace preserves previous runs; exported IDs stay stable.
    run_id = f"{scenario.scenario_id}:{baseline}:{seed}:{uuid4().hex}"
    ledger: Ledger = (
        MemoryLedger(run_id) if database_url is None else PostgresLedger(database_url, run_id)
    )
    if isinstance(ledger, PostgresLedger):
        await ledger.migrate()
    probe = ConcurrencyProbe(
        require_overlap=scenario.require_provider_overlap,
        hold_until_release=scenario.scenario_id == "disjoint_resource_compensation",
    )
    turns = [asyncio.Event() for _ in scenario.workflows]
    turns[0].set()
    index_by_id = {intent.effect_id: index for index, intent in enumerate(scenario.workflows)}

    def on_admission(intent: EffectIntent) -> None:
        index = index_by_id[intent.effect_id]
        if index + 1 < len(turns):
            turns[index + 1].set()
        if index == len(turns) - 1 and probe.hold_until_release:
            probe.release.set()

    try:
        async with local_services(
            scenario.fault_schedule,
            probe,
            {contract.operation: contract for contract in scenario.tool_contracts},
        ) as (adapter, providers):
            runtime = Coordinator(ledger, adapter, policy_for(baseline, scenario), on_admission)
            if scenario.scenario_id.startswith("ambiguous_payment"):
                ambiguous = asyncio.Event()
                shipment_done = asyncio.Event()
                payment, shipment = scenario.workflows

                async def payment_agent() -> None:
                    try:
                        await runtime.submit(payment)
                    finally:
                        ambiguous.set()
                    await shipment_done.wait()

                async def shipping_agent() -> None:
                    try:
                        await ambiguous.wait()
                        await runtime.submit(shipment)
                    finally:
                        shipment_done.set()

                async with asyncio.timeout(15):
                    await asyncio.gather(payment_agent(), shipping_agent())
            else:
                # Both scripted agents prepare from the same initial version snapshot.
                ready = asyncio.Barrier(len(scenario.workflows))

                async def agent(index: int) -> None:
                    await ready.wait()
                    await turns[index].wait()
                    await runtime.submit(scenario.workflows[index])

                async with asyncio.timeout(15):
                    await asyncio.gather(
                        *(agent(index) for index in range(len(scenario.workflows)))
                    )
            records = await ledger.effects()
            events = await ledger.events()
            journal = providers[Operation.CHARGE].journal
            metrics = evaluate(scenario, records, events, journal, probe.max_in_flight)
        trace_name = await asyncio.to_thread(
            write_trace, output, scenario.scenario_id, baseline, events, journal
        )
        return RunResult(
            scenario_id=scenario.scenario_id,
            baseline=baseline,
            seed=seed,
            scenario_sha256=scenario_hash(scenario),
            metrics=metrics,
            trace_file=trace_name,
        )
    finally:
        await ledger.close()


def write_trace(
    output: Path,
    scenario_id: str,
    baseline: str,
    events: list[LedgerEvent],
    journal: list[ProviderEffect],
) -> str:
    output.mkdir(parents=True, exist_ok=True)
    trace_name = f"{scenario_id}__{baseline}.jsonl"
    rows = [
        {"kind": "runtime", **event.model_dump(mode="json", exclude={"run_id"})} for event in events
    ] + [
        {"kind": "provider", "commit_sequence": index, **effect.model_dump(mode="json")}
        for index, effect in enumerate(journal, start=1)
    ]
    (output / trace_name).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return trace_name
