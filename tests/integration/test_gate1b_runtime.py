import os
from pathlib import Path

import httpx
import pytest

from agenttxn.adapters.direct import DirectAdapter
from agenttxn.contracts.models import ToolContract, ToolRequest
from agenttxn.effects.models import Operation
from agenttxn.effects.outcomes import ALL_OUTCOMES, ExternalOutcome
from baselines.uncertainty import POLICIES
from services.common import create_app
from services.uncertainty import Realization, ScheduledUncertainProvider
from txnagentbench.commerce.gate1b import problems
from txnagentbench.uncertainty_runner import run_uncertainty

pytestmark = pytest.mark.integration


async def test_all_hidden_realizations_return_identical_ambiguous_http_observations() -> None:
    responses = []
    request = ToolRequest(logical_operation_id="upstream", order_id="o", amount_cents=100)
    for realization in Realization:
        provider = ScheduledUncertainProvider(Operation.CHARGE, realization, [])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(provider)), base_url="http://mock"
        ) as client:
            result = await client.post("/effects", json=request.model_dump(mode="json"))
            probe = await client.get("/operations/upstream")
            responses.append((result.status_code, result.json(), probe.json()))
            assert provider.reconcile("upstream").possible_outcomes == ALL_OUTCOMES
    assert all(response == responses[0] for response in responses)


async def test_idempotent_inflight_retry_cannot_duplicate_or_resurrect_a_terminal_abort() -> None:
    provider = ScheduledUncertainProvider(Operation.CHARGE, Realization.TERMINAL_ABORT, [])
    request = ToolRequest(logical_operation_id="upstream", order_id="o", amount_cents=100)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(provider)), base_url="http://mock"
    ) as client:
        assert (
            await client.post("/effects", json=request.model_dump(mode="json"))
        ).status_code == 504
        for _ in range(3):
            result = await client.post("/effects", json=request.model_dump(mode="json"))
            assert result.json()["certainty"] == "UNKNOWN"
        assert len(provider.pending) == 1
        assert not provider.journal
        provider.advance(1)
        provider.advance(2)
        provider.advance(3)
        assert provider.real_outcome == ExternalOutcome.ABSENT
        result = await client.post("/effects", json=request.model_dump(mode="json"))
        assert result.json()["certainty"] == "FAILED"
        assert not provider.effects and not provider.pending
        with pytest.raises(KeyError):
            provider.settle_pending("upstream", commit=True)


async def test_postgres_gate1b_metrics_and_observations_match_memory(tmp_path: Path) -> None:
    url = os.environ.get("AGENTTXN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AGENTTXN_TEST_DATABASE_URL is required for PostgreSQL integration")
    problem = problems()[1]
    memory = await run_uncertainty(
        problem, Realization.LATE_COMMIT, POLICIES[-1], 42, tmp_path / "memory"
    )
    persistent = await run_uncertainty(
        problem, Realization.LATE_COMMIT, POLICIES[-1], 42, tmp_path / "postgres", url
    )
    assert memory.metrics == persistent.metrics
    assert memory.input_hashes == persistent.input_hashes
    assert memory.max_candidate_calls_in_flight == persistent.max_candidate_calls_in_flight


async def test_missing_quiescence_capability_cannot_eliminate_inflight_world() -> None:
    provider = ScheduledUncertainProvider(Operation.CHARGE, Realization.HIDDEN_ABSENT, [])
    provider.advance(1)
    provider.advance(2)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(provider)), base_url="http://mock"
    ) as client:
        adapter = DirectAdapter(
            {Operation.CHARGE: client},
            {
                Operation.CHARGE: ToolContract(
                    operation=Operation.CHARGE, quiescence_certificate_supported=False
                ),
            },
        )
        result = await adapter.reconcile(problems()[0].upstream)
        assert result.possible_outcomes == ALL_OUTCOMES
