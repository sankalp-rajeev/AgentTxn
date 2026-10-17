"""Reproduce week-one ambiguity, disjoint-resource conflicts, and concurrency controls."""

import argparse
import asyncio
import json
import os
import platform
from pathlib import Path

from txnagentbench.commerce.week1 import scenarios
from txnagentbench.provenance import source_provenance
from txnagentbench.runner import BASELINES, RunResult, run_scenario
from txnagentbench.schema import Scenario


async def run(args: argparse.Namespace) -> list[RunResult]:
    selected = BASELINES if args.baseline == "all" else (args.baseline,)
    definitions = scenarios(args.seed)
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if args.ledger == "postgres" and not database_url:
        raise ValueError("--ledger postgres requires DATABASE_URL or --database-url")
    results = []
    for scenario in definitions:
        print(f"Scenario: {scenario.scenario_id}", flush=True)
        for baseline in selected:
            result = await run_scenario(
                scenario,
                baseline,
                args.seed,
                args.output,
                database_url if args.ledger == "postgres" else None,
            )
            results.append(result)
            metrics = result.metrics
            print(
                f"  {baseline}: violations={metrics.invariant_violations} "
                f"unsafe_downstream={metrics.unsafe_downstream_actions} "
                f"effects={metrics.committed_external_effects} "
                f"max_in_flight={metrics.max_provider_calls_in_flight} "
                f"success={metrics.task_success}",
                flush=True,
            )
    await asyncio.to_thread(write_manifest, args, definitions, results)
    print(f"Evidence: {args.output / 'summary.json'}", flush=True)
    return results


def write_manifest(
    args: argparse.Namespace, definitions: list[Scenario], results: list[RunResult]
) -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = {
        "benchmark_version": "week1-v1",
        "seed": args.seed,
        "ledger": args.ledger,
        "python": platform.python_version(),
        **source_provenance(root),
        "determinism_scope": (
            "Seeded inputs, faults, and admission order; "
            "PostgreSQL completion events may interleave"
        ),
        "scenarios": [scenario.model_dump(mode="json") for scenario in definitions],
        "results": [result.model_dump(mode="json") for result in results],
    }
    (args.output / "summary.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--baseline", choices=("all", *BASELINES), default="all")
    parser.add_argument("--ledger", choices=("memory", "postgres"), default="memory")
    parser.add_argument(
        "--database-url", help="PostgreSQL URL; prefer DATABASE_URL for local secrets"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/week1"))
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
