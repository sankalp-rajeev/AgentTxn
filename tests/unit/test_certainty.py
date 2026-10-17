import pytest

from agenttxn.effects.certainty import Certainty, validate_transition
from agenttxn.effects.ledger import MemoryLedger
from agenttxn.effects.models import EffectIntent, Operation


def intent(effect_id: str = "charge") -> EffectIntent:
    return EffectIntent(
        effect_id=effect_id,
        logical_operation_id=effect_id,
        transaction_id="txn",
        agent_id="agent",
        workflow_id="workflow",
        operation=Operation.CHARGE,
        order_id="order",
        amount_cents=100,
        resource_footprint=("payment:order",),
    )


@pytest.mark.parametrize("after", [Certainty.CONFIRMED, Certainty.FAILED])
def test_unknown_requires_evidence_before_resolution(after: Certainty) -> None:
    validate_transition(Certainty.UNKNOWN, after)
    with pytest.raises(ValueError):
        validate_transition(Certainty.UNKNOWN, Certainty.PENDING)


async def test_ledger_does_not_reexecute_an_ambiguous_registration() -> None:
    ledger = MemoryLedger("test")
    await ledger.register(intent())
    await ledger.transition("charge", Certainty.PENDING, "Request submitted")
    await ledger.transition("charge", Certainty.UNKNOWN, "Acknowledgement lost")
    record = await ledger.register(intent())
    assert record.certainty == Certainty.UNKNOWN
    assert len(await ledger.events()) == 3
    with pytest.raises(ValueError):
        await ledger.register(intent().model_copy(update={"amount_cents": 200}))
    assert len(await ledger.events()) == 3


async def test_invalid_transition_has_no_partial_event_or_state() -> None:
    ledger = MemoryLedger("test")
    await ledger.register(intent())
    with pytest.raises(ValueError):
        await ledger.transition("charge", Certainty.CONFIRMED, "Invalid shortcut")
    assert (await ledger.get("charge")).certainty == Certainty.NOT_STARTED
    assert len(await ledger.events()) == 1
