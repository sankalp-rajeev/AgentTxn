from pathlib import Path

import pytest

from txnagentbench.commerce.week1 import scenarios
from txnagentbench.runner import BASELINES, run_scenario

pytestmark = pytest.mark.benchmark_smoke


@pytest.mark.parametrize("baseline", BASELINES)
async def test_budget_race_and_metadata_control_are_reported_honestly(
    baseline: str, tmp_path: Path
) -> None:
    scenario = next(
        item for item in scenarios(42) if item.scenario_id == "disjoint_resource_compensation"
    )
    result = await run_scenario(scenario, baseline, 42, tmp_path)
    assert result.metrics.invariant_violations == (baseline in {"naive", "resource_occ"})
    assert result.metrics.committed_external_effects == (
        2 if baseline in {"naive", "resource_occ"} else 1
    )


async def test_seed_replays_memory_trace_exactly(tmp_path: Path) -> None:
    for scenario in scenarios(42):
        first = await run_scenario(scenario, "agenttxn", 42, tmp_path / "first")
        second = await run_scenario(scenario, "agenttxn", 42, tmp_path / "second")
        assert first == second
        assert (tmp_path / "first" / first.trace_file).read_bytes() == (
            tmp_path / "second" / second.trace_file
        ).read_bytes()
        assert first.metrics.task_success
