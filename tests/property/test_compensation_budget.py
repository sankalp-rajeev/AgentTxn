import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from agenttxn.effects.ledger import MemoryLedger
from agenttxn.effects.models import Operation
from agenttxn.runtime.certifier import SemanticCertifier
from agenttxn.runtime.coordinator import Coordinator
from txnagentbench.commerce.week1 import financial_intent
from txnagentbench.local import local_services


@settings(max_examples=30, deadline=None, derandomize=True)
@given(
    budget=st.integers(min_value=1, max_value=100000),
    refund=st.integers(min_value=1, max_value=100000),
    credit=st.integers(min_value=1, max_value=100000),
)
def test_concurrent_admission_never_oversubscribes_budget(
    budget: int, refund: int, credit: int
) -> None:
    async def check() -> None:
        async with local_services() as (adapter, providers):
            runtime = Coordinator(
                MemoryLedger("property"), adapter, SemanticCertifier({"incident-1": budget})
            )
            await asyncio.gather(
                runtime.submit(financial_intent(Operation.REFUND, "refund", amount_cents=refund)),
                runtime.submit(financial_intent(Operation.CREDIT, "credit", amount_cents=credit)),
            )
            total = sum(
                effect.request.amount_cents for effect in providers[Operation.CHARGE].journal
            )
            assert total <= budget

    asyncio.run(check())
