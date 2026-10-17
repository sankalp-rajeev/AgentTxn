import pytest
from pydantic import ValidationError

from agenttxn.effects.certainty import Certainty
from agenttxn.effects.ledger import MemoryLedger
from agenttxn.effects.models import EffectIntent, Operation
from agenttxn.effects.outcomes import ALL_OUTCOMES, QUIESCENT_OUTCOMES, ExternalOutcome, OutcomeSet


@pytest.mark.parametrize("values", [(), (ExternalOutcome.ABSENT, ExternalOutcome.ABSENT)])
def test_outcome_set_rejects_vacuous_and_duplicate_worlds(
    values: tuple[ExternalOutcome, ...],
) -> None:
    with pytest.raises(ValidationError):
        OutcomeSet(values=values)


async def test_refinement_preserves_unknown_until_authoritative_terminal_evidence() -> None:
    ledger = MemoryLedger("outcomes")
    intent = EffectIntent(
        effect_id="u",
        logical_operation_id="u",
        transaction_id="t",
        agent_id="a",
        workflow_id="w",
        operation=Operation.CHARGE,
        order_id="o",
        amount_cents=100,
        resource_footprint=("payment:o",),
    )
    await ledger.register(intent)
    await ledger.transition("u", Certainty.PENDING, "Submitted")
    await ledger.transition("u", Certainty.UNKNOWN, "Timeout")
    await ledger.refine_outcomes("u", ALL_OUTCOMES, "Opaque timeout")
    result = await ledger.refine_outcomes(
        "u", QUIESCENT_OUTCOMES, "No in-flight writes certificate"
    )
    assert result.certainty == Certainty.UNKNOWN
    assert result.possible_outcomes == QUIESCENT_OUTCOMES
    count = len(await ledger.events())
    with pytest.raises(ValueError, match="reintroduce"):
        await ledger.refine_outcomes("u", ALL_OUTCOMES, "Invalid widening")
    assert len(await ledger.events()) == count
    result = await ledger.refine_outcomes(
        "u", OutcomeSet(values=(ExternalOutcome.ABSENT,)), "Authoritative terminal abort receipt"
    )
    assert result.certainty == Certainty.FAILED
    assert (await ledger.events())[-1].possible_outcomes == result.possible_outcomes
