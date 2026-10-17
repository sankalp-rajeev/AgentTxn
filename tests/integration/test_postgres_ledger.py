import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from agenttxn.effects.certainty import Certainty
from agenttxn.effects.models import EffectIntent, Operation
from agenttxn.effects.outcomes import ALL_OUTCOMES, QUIESCENT_OUTCOMES, ExternalOutcome, OutcomeSet
from agenttxn.effects.postgres import PostgresLedger

pytestmark = pytest.mark.integration


async def test_postgres_reopens_state_and_protects_append_only_events() -> None:
    url = os.environ.get("AGENTTXN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AGENTTXN_TEST_DATABASE_URL is required for PostgreSQL integration")
    run_id = f"ledger-test-{uuid4()}"
    ledger = PostgresLedger(url, run_id)
    intent = EffectIntent(
        effect_id="charge",
        logical_operation_id="charge",
        transaction_id="txn",
        agent_id="agent",
        workflow_id="workflow",
        operation=Operation.CHARGE,
        order_id="order",
        amount_cents=100,
        resource_footprint=("payment:order",),
    )
    try:
        await ledger.migrate()
        await ledger.migrate()
        await ledger.register(intent)
        await ledger.transition("charge", Certainty.PENDING, "Submitted")
        await ledger.transition("charge", Certainty.UNKNOWN, "Timed out", "HTTP 504")
        with pytest.raises(ValueError):
            await ledger.transition("charge", Certainty.PENDING, "Unsafe retry")
        assert (await ledger.get("charge")).certainty == Certainty.UNKNOWN
        assert len(await ledger.events()) == 3
    finally:
        await ledger.close()

    reopened = PostgresLedger(url, run_id)
    try:
        assert (await reopened.register(intent)).certainty == Certainty.UNKNOWN
        await reopened.transition("charge", Certainty.CONFIRMED, "Provider truth", "Found charge")
        events = await reopened.events()
        assert [event.sequence for event in events] == [1, 2, 3, 4]
        assert events[-1].certainty_state_before == Certainty.UNKNOWN
        assert events[-1].observation == "Found charge"
        async with reopened.engine.begin() as conn:
            count = await conn.scalar(
                text("SELECT COUNT(*) FROM effect_observations WHERE run_id = :run_id"),
                {"run_id": run_id},
            )
            assert count == 2
        with pytest.raises(DBAPIError, match="append-only"):
            async with reopened.engine.begin() as conn:
                await conn.execute(
                    text("UPDATE effect_events SET event = '{}' WHERE run_id = :run_id"),
                    {"run_id": run_id},
                )
    finally:
        await reopened.close()


async def test_possible_outcomes_survive_reopen_and_invalid_refinement_rolls_back() -> None:
    url = os.environ.get("AGENTTXN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("AGENTTXN_TEST_DATABASE_URL is required for PostgreSQL integration")
    run_id = f"outcome-test-{uuid4()}"
    ledger = PostgresLedger(url, run_id)
    intent = EffectIntent(
        effect_id="u",
        logical_operation_id="u",
        transaction_id="t",
        agent_id="a",
        workflow_id="w",
        operation=Operation.REFUND,
        incident_id="i",
        amount_cents=30000,
        resource_footprint=("refund:u",),
    )
    try:
        await ledger.migrate()
        await ledger.register(intent)
        await ledger.transition("u", Certainty.PENDING, "Submitted")
        await ledger.transition("u", Certainty.UNKNOWN, "Timeout")
        await ledger.refine_outcomes("u", ALL_OUTCOMES, "Unresolved")
        await ledger.refine_outcomes("u", QUIESCENT_OUTCOMES, "Quiescence proof")
    finally:
        await ledger.close()
    reopened = PostgresLedger(url, run_id)
    try:
        assert (await reopened.get("u")).possible_outcomes == QUIESCENT_OUTCOMES
        assert (await reopened.get("u")).certainty == Certainty.UNKNOWN
        count = len(await reopened.events())
        with pytest.raises(ValueError, match="reintroduce"):
            await reopened.refine_outcomes("u", ALL_OUTCOMES, "Invalid")
        assert len(await reopened.events()) == count
        terminal = await reopened.refine_outcomes(
            "u", OutcomeSet(values=(ExternalOutcome.COMMITTED,)), "Receipt"
        )
        assert terminal.certainty == Certainty.CONFIRMED
        assert terminal.possible_outcomes == OutcomeSet(values=(ExternalOutcome.COMMITTED,))
    finally:
        await reopened.close()
