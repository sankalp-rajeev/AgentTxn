import json
from pathlib import Path

import pytest

from agenttxn.effects.models import Decision
from agenttxn.runtime.outcome_admission import OutcomeAdmissionPolicy
from agenttxn.runtime.uncertainty import Assessment, Candidate
from baselines.uncertainty import POLICIES
from services.uncertainty import Realization
from txnagentbench.commerce.gate1b import problems
from txnagentbench.uncertainty_replay import verify_summary
from txnagentbench.uncertainty_runner import run_uncertainty

pytestmark = pytest.mark.benchmark_smoke


@pytest.mark.parametrize("index", [0, 1])
async def test_full_matched_policy_and_fault_matrix(index: int, tmp_path: Path) -> None:
    problem = problems()[index]
    indistinguishable = None
    for realization in Realization:
        matched = None
        for policy in POLICIES:
            result = await run_uncertainty(problem, realization, policy, 42, tmp_path)
            metrics = result.metrics
            assert metrics.decision_opportunities == 32
            assert metrics.unsafe_admissions == metrics.physical_violation_events == 0
            assert metrics.duplicate_effects == metrics.irrecoverable_residue_events == 0
            safe_opportunities = 10 if index == 0 else 13
            assert metrics.pre_resolution_safe_opportunities == safe_opportunities
            if policy.name == "global_fail_closed":
                assert metrics.safe_opportunities_unnecessarily_blocked == safe_opportunities
                assert metrics.safe_actions_admitted_before_resolution == 0
            else:
                assert metrics.safe_opportunities_unnecessarily_blocked == 0
                assert metrics.safe_actions_admitted_before_resolution == (4 if index == 0 else 5)
            if matched is not None:
                assert matched == result.input_hashes
            matched = result.input_hashes
            if indistinguishable is not None:
                assert result.input_hashes[:3] == indistinguishable
            indistinguishable = result.input_hashes[:3]
            rows = [
                json.loads(line) for line in (tmp_path / result.trace_file).read_text().splitlines()
            ]
            panel = [row for row in rows if row["kind"] == "decision_panel"]
            assert len(panel) == 32
            assert all(row["oracle_safe"] for row in panel if row["decision"] == Decision.COMMIT)


async def test_seed_replays_gate1b_memory_trace_exactly(tmp_path: Path) -> None:
    for problem in problems():
        first = await run_uncertainty(
            problem, Realization.LATE_COMMIT, POLICIES[-1], 42, tmp_path / "first"
        )
        second = await run_uncertainty(
            problem, Realization.LATE_COMMIT, POLICIES[-1], 42, tmp_path / "second"
        )
        assert first == second
        assert (tmp_path / "first" / first.trace_file).read_bytes() == (
            tmp_path / "second" / second.trace_file
        ).read_bytes()
        rows = [
            json.loads(line)
            for line in (tmp_path / "first" / first.trace_file).read_text().splitlines()
        ]
        truth = [row["real_outcome"] for row in rows if row["kind"] == "provider_checkpoint"]
        assert truth == ["IN_FLIGHT", "IN_FLIGHT", "COMMITTED", "COMMITTED"]
        evidence = [
            row["observation"]["outcomes"]["values"] for row in rows if row["kind"] == "evidence"
        ]
        assert evidence[2] == ["ABSENT", "COMMITTED"]
        assert evidence[3] == ["COMMITTED"]


async def test_negative_control_produces_unsafe_commits_and_replayable_physical_violations(
    tmp_path: Path,
) -> None:
    class AlwaysAllow(OutcomeAdmissionPolicy):
        name = "test_only_unsafe_negative_control"

        def assess(self, candidate: Candidate) -> Assessment:
            return Assessment(decision=Decision.COMMIT, reason="Deliberately unsafe test control")

    problem = problems()[0]
    result = await run_uncertainty(problem, Realization.LATE_COMMIT, AlwaysAllow, 42, tmp_path)
    assert result.metrics.unsafe_admissions > 0
    assert result.metrics.physical_violation_events > 0
    (tmp_path / "summary.json").write_text(
        json.dumps(
            {
                "scenarios": [problem.model_dump(mode="json")],
                "results": [result.model_dump(mode="json")],
            }
        ),
        encoding="utf-8",
    )
    assert verify_summary(tmp_path) == 1
