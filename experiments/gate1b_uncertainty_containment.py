"""Run the matched-information Gate-1B uncertainty-containment feasibility test."""

import argparse
import asyncio
import hashlib
import json
import os
import platform
from itertools import combinations
from pathlib import Path

from pydantic import JsonValue

from agenttxn.effects.outcomes import ExternalOutcome, OutcomeSet
from agenttxn.runtime.uncertainty import AdmissionView, Observation
from baselines.uncertainty import POLICIES
from services.uncertainty import Realization
from txnagentbench.commerce.gate1b import problems
from txnagentbench.oracle import joint_subset_audit
from txnagentbench.provenance import source_provenance
from txnagentbench.uncertainty_replay import verify_summary
from txnagentbench.uncertainty_runner import UncertaintyRun, run_uncertainty


def equivalence_audit() -> dict[str, JsonValue]:
    comparisons = {policy.name: 0 for policy in POLICIES[:-1]}
    differences = {policy.name: 0 for policy in POLICIES[:-1]}
    subsets = 0
    for problem in problems():
        for size in range(1, 4):
            for values in combinations(tuple(ExternalOutcome), size):
                outcomes = OutcomeSet(values=values)
                subsets += joint_subset_audit(problem, outcomes)
                view = AdmissionView(
                    problem=problem,
                    observations=(
                        Observation(
                            round=0, description="Exhaustive outcome-set audit", outcomes=outcomes
                        ),
                    ),
                )
                policies = [policy(view) for policy in POLICIES]
                for candidate in problem.candidates:
                    expected = policies[-1].assess(candidate).decision
                    for policy in policies[:-1]:
                        comparisons[policy.name] += 1
                        differences[policy.name] += policy.assess(candidate).decision != expected
    return {
        "candidate_outcome_cases_per_policy": next(iter(comparisons.values())),
        "comparisons": dict(comparisons),
        "decision_differences_from_oca": dict(differences),
        "joint_safe_subsets_checked": subsets,
    }


async def run(args: argparse.Namespace) -> list[UncertaintyRun]:
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if args.ledger == "postgres" and not database_url:
        raise ValueError("PostgreSQL execution requires DATABASE_URL or --database-url")
    selected = [policy for policy in POLICIES if args.baseline in {"all", policy.name}]
    definitions = [
        problem for problem in problems() if args.scenario in {"all", problem.scenario_id}
    ]
    realizations = [item for item in Realization if args.realization in {"all", str(item)}]
    results = []
    for problem in definitions:
        for realization in realizations:
            print(
                f"Scenario: {problem.scenario_id}; hidden provider realization: {realization}",
                flush=True,
            )
            matched: tuple[str, ...] | None = None
            for policy in selected:
                result = await run_uncertainty(
                    problem,
                    realization,
                    policy,
                    args.seed,
                    args.output,
                    database_url if args.ledger == "postgres" else None,
                )
                if matched is not None and result.input_hashes != matched:
                    raise ValueError("Policies received different metadata or observation streams")
                matched = result.input_hashes
                results.append(result)
                metrics = result.metrics
                print(
                    f"  {result.baseline}: unsafe={metrics.unsafe_admissions} "
                    f"physical={metrics.physical_violation_events} "
                    f"collateral={metrics.safe_opportunities_unnecessarily_blocked}/"
                    f"{metrics.pre_resolution_safe_opportunities} "
                    f"safe_before_resolution={metrics.safe_actions_admitted_before_resolution}",
                    flush=True,
                )
    await asyncio.to_thread(write_summary, args, results)
    return results


def write_summary(args: argparse.Namespace, results: list[UncertaintyRun]) -> None:
    root = Path(__file__).resolve().parents[1]
    documents = (
        "AgentTxn_Redesign_Deep_Dive.md",
        "experiments/week1.md",
        "AgentTxn_PRD.md",
        "experiments/gate1b_protocol.md",
    )
    summary = {
        "benchmark_version": "gate1b-v1",
        "seed": args.seed,
        "ledger": args.ledger,
        "python": platform.python_version(),
        **source_provenance(root),
        "input_document_sha256_lf": {
            name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in documents
        },
        "determinism_scope": (
            "Frozen evidence rounds, seeded admission order; "
            "commuting PostgreSQL events may interleave"
        ),
        "scenarios": [problem.model_dump(mode="json") for problem in problems()],
        "realizations": [str(item) for item in Realization],
        "equivalence_audit": equivalence_audit(),
        "results": [result.model_dump(mode="json") for result in results],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    verified = verify_summary(args.output)
    if verified != len(results):
        raise ValueError("Raw evidence replay did not verify every collected condition")
    if args.report:
        if len(results) != 48:
            raise ValueError("A complete Gate-1B report requires all 48 matched conditions")
        from experiments.gate1b_report import write_report

        write_report(summary, args.report, args.output)
    print(f"Evidence: {args.output / 'summary.json'}", flush=True)
    print(f"Replay-verified conditions: {verified}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--baseline", choices=("all", *(policy.name for policy in POLICIES)), default="all"
    )
    parser.add_argument(
        "--scenario", choices=("all", *(item.scenario_id for item in problems())), default="all"
    )
    parser.add_argument(
        "--realization", choices=("all", *(str(item) for item in Realization)), default="all"
    )
    parser.add_argument("--ledger", choices=("memory", "postgres"), default="memory")
    parser.add_argument("--database-url", help="Prefer DATABASE_URL for credentials")
    parser.add_argument("--output", type=Path, default=Path("artifacts/gate1b"))
    parser.add_argument(
        "--report", type=Path, help="Write a report only after running every condition"
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
