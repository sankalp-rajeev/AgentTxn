"""Gate-1B phased concurrent harness reusing Week-1 ledger, coordinator, adapter, and HTTP mocks."""

import asyncio
import json
import random
from contextlib import AsyncExitStack
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic import BaseModel

from agenttxn.adapters.direct import DirectAdapter
from agenttxn.contracts.models import ToolContract
from agenttxn.effects.certainty import Certainty
from agenttxn.effects.ledger import Ledger, MemoryLedger
from agenttxn.effects.models import EffectIntent, LedgerEvent, Operation
from agenttxn.effects.postgres import PostgresLedger
from agenttxn.metrics.collateral import ContainmentMetrics, DecisionSample, containment_metrics
from agenttxn.runtime.coordinator import Coordinator
from agenttxn.runtime.outcome_admission import OutcomeAdmissionPolicy, view_hash
from agenttxn.runtime.uncertainty import AdmissionView, Candidate, MatchedProblem, Observation
from baselines.naive import NaivePolicy
from services.common import ConcurrencyProbe, MockProvider, ProviderEffect, create_app
from services.uncertainty import Realization, ScheduledUncertainProvider
from txnagentbench.oracle import oracle_safe, violations


class UncertaintyRun(BaseModel):
    scenario_id: str
    realization: Realization
    baseline: str
    seed: int
    metrics: ContainmentMetrics
    trace_file: str
    input_hashes: tuple[str, ...]
    max_candidate_calls_in_flight: int


async def execute_round(
    ledger: Ledger,
    adapter: DirectAdapter,
    policy: OutcomeAdmissionPolicy,
    ready: list[Candidate],
    probe: ConcurrencyProbe,
) -> None:
    if not ready:
        return
    probe.release.clear()
    turns = [asyncio.Event() for _ in ready]
    turns[0].set()
    positions = {item.intent.effect_id: index for index, item in enumerate(ready)}

    def on_admission(intent: EffectIntent) -> None:
        index = positions[intent.effect_id]
        if index + 1 < len(turns):
            turns[index + 1].set()
        else:
            probe.release.set()

    runtime = Coordinator(ledger, adapter, policy, on_admission)
    barrier = asyncio.Barrier(len(ready))

    async def agent(index: int, candidate: Candidate) -> None:
        await barrier.wait()
        await turns[index].wait()
        result = await runtime.submit(candidate.intent, wait_for_evidence=False)
        expected = policy.assess(candidate).decision
        if result.decision != expected:
            raise ValueError("Execution and recorded policy decision diverged")

    async with asyncio.timeout(30):
        await asyncio.gather(*(agent(index, item) for index, item in enumerate(ready)))


async def run_uncertainty(
    problem: MatchedProblem,
    realization: Realization,
    policy_type: type[OutcomeAdmissionPolicy],
    seed: int,
    output: Path,
    database_url: str | None = None,
) -> UncertaintyRun:
    storage_id = f"gate1b:{problem.scenario_id}:{realization}:{policy_type.name}:{uuid4().hex}"
    ledger: Ledger = (
        MemoryLedger(storage_id)
        if database_url is None
        else PostgresLedger(database_url, storage_id)
    )
    if isinstance(ledger, PostgresLedger):
        await ledger.migrate()
    journal: list[ProviderEffect] = []
    upstream = ScheduledUncertainProvider(problem.upstream.operation, realization, journal)
    probe = ConcurrencyProbe(hold_until_release=True)
    candidate_provider = MockProvider(Operation.CANDIDATE, probe=probe, journal=journal)
    observations: list[Observation] = []
    input_hashes: list[str] = []
    panel: list[DecisionSample] = []
    committed: set[str] = set()
    physical_events: list[dict[str, object]] = []
    trace: list[dict[str, object]] = []
    candidates = list(problem.candidates)
    random.Random(seed).shuffle(candidates)
    by_id = {item.intent.effect_id: item for item in candidates}
    try:
        async with AsyncExitStack() as stack:
            clients = {
                operation: await stack.enter_async_context(
                    httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=create_app(provider)),
                        base_url="http://mock",
                    )
                )
                for operation, provider in (
                    (problem.upstream.operation, upstream),
                    (Operation.CANDIDATE, candidate_provider),
                )
            }
            adapter = DirectAdapter(
                clients,
                {
                    problem.upstream.operation: problem.upstream_contract,
                    Operation.CANDIDATE: ToolContract(operation=Operation.CANDIDATE),
                },
            )
            bootstrap = Coordinator(ledger, adapter, NaivePolicy())
            await bootstrap.submit(problem.upstream)
            if (await ledger.get("upstream")).certainty != Certainty.UNKNOWN:
                raise ValueError("The surgical experiment requires a genuinely unresolved request")
            for round_number in range(4):
                if round_number:
                    upstream.advance(round_number)
                evidence = await adapter.reconcile(problem.upstream)
                if evidence.possible_outcomes is None:
                    raise ValueError(
                        "Gate-1B receipts must specify their evidence-compatible outcome set"
                    )
                await ledger.refine_outcomes(
                    "upstream", evidence.possible_outcomes, evidence.model_dump_json()
                )
                observations.append(
                    Observation(
                        round=round_number,
                        description=evidence.reason,
                        outcomes=evidence.possible_outcomes,
                    )
                )
                view = AdmissionView(problem=problem, observations=tuple(observations))
                input_hashes.append(view_hash(view))
                policy = policy_type(view)
                trace.append(
                    {
                        "kind": "evidence",
                        "observation": observations[-1].model_dump(mode="json"),
                        "input_sha256": input_hashes[-1],
                    }
                )
                for candidate in candidates:
                    assessment = policy.assess(candidate)
                    panel.append(
                        DecisionSample(
                            round=round_number,
                            candidate_id=candidate.intent.effect_id,
                            input_sha256=input_hashes[-1],
                            possible_outcomes=tuple(str(item) for item in view.outcomes.values),
                            oracle_safe=oracle_safe(problem, candidate, view.outcomes),
                            decision=assessment.decision,
                            already_executed=candidate.intent.effect_id in committed,
                            reason=assessment.reason,
                            coordination_scopes=assessment.coordination_scopes,
                            blocked_scopes=assessment.blocked_scopes,
                        )
                    )
                # Check lingering effects when a formerly in-flight request settles.
                active = tuple(by_id[item] for item in sorted(committed))
                bad = violations(problem, active, upstream.real_outcome)
                if bad:
                    physical_events.append(
                        {"round": round_number, "kind": "upstream_resolution", "violations": bad}
                    )
                ready = [item for item in candidates if item.intent.effect_id not in committed]
                await execute_round(ledger, adapter, policy, ready, probe)
                actual = [item for item in journal if item.operation == Operation.CANDIDATE]
                old = set(committed)
                for effect in actual:
                    name = effect.request.action_name
                    if name is None:
                        raise ValueError("Candidate provider receipt has no action identity")
                    if name not in old:
                        committed.add(name)
                        bad = violations(
                            problem,
                            tuple(by_id[item] for item in sorted(committed)),
                            upstream.real_outcome,
                        )
                        if bad:
                            physical_events.append(
                                {
                                    "round": round_number,
                                    "kind": "candidate_commit",
                                    "candidate": name,
                                    "violations": bad,
                                }
                            )
                if view_hash(view) != input_hashes[-1]:
                    raise ValueError("An admission policy mutated its matched input")
                trace.append(
                    {
                        "kind": "provider_checkpoint",
                        "round": round_number,
                        "real_outcome": str(upstream.real_outcome),
                        "candidate_commit_ids": sorted(committed),
                        "provider_journal_length": len(journal),
                    }
                )
            events = await ledger.events()
        commit_ids = [
            str(item.request.action_name)
            for item in journal
            if item.operation == Operation.CANDIDATE
        ]
        metrics = containment_metrics(panel, commit_ids, len(physical_events))
        trace_name = f"{problem.scenario_id}__{realization}__{policy_type.name}.jsonl"
        await asyncio.to_thread(
            write_uncertainty_trace,
            output / trace_name,
            trace,
            panel,
            events,
            journal,
            physical_events,
        )
        return UncertaintyRun(
            scenario_id=problem.scenario_id,
            realization=realization,
            baseline=policy_type.name,
            seed=seed,
            metrics=metrics,
            trace_file=trace_name,
            input_hashes=tuple(input_hashes),
            max_candidate_calls_in_flight=probe.max_in_flight,
        )
    finally:
        await ledger.close()


def write_uncertainty_trace(
    path: Path,
    checkpoints: list[dict[str, object]],
    panel: list[DecisionSample],
    events: list[LedgerEvent],
    journal: list[ProviderEffect],
    physical: list[dict[str, object]],
) -> None:
    rows = (
        checkpoints
        + [{"kind": "decision_panel", **item.model_dump(mode="json")} for item in panel]
        + [
            {"kind": "runtime", **item.model_dump(mode="json", exclude={"run_id"})}
            for item in events
        ]
        + [
            {"kind": "provider_commit", "sequence": index, **item.model_dump(mode="json")}
            for index, item in enumerate(journal, start=1)
        ]
        + [
            {**item, "violation_kind": item["kind"], "kind": "physical_violation"}
            for item in physical
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
