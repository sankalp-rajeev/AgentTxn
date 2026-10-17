"""In-process HTTP service composition; providers retain independent truth."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

import httpx

from agenttxn.adapters.direct import DirectAdapter
from agenttxn.contracts.models import ToolContract, week1_contracts
from agenttxn.effects.models import Operation
from agenttxn.faults.injector import Fault, FaultInjector
from services.common import ConcurrencyProbe, MockProvider, ProviderEffect, create_app


@asynccontextmanager
async def local_services(
    faults: dict[str, Fault] | None = None,
    probe: ConcurrencyProbe | None = None,
    contracts: dict[Operation, ToolContract] | None = None,
) -> AsyncIterator[tuple[DirectAdapter, dict[Operation, MockProvider]]]:
    journal: list[ProviderEffect] = []
    providers = {
        operation: MockProvider(operation, FaultInjector(faults), probe, journal)
        for operation in Operation
    }
    async with AsyncExitStack() as stack:
        clients = {
            operation: await stack.enter_async_context(
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=create_app(provider)), base_url="http://mock"
                )
            )
            for operation, provider in providers.items()
        }
        yield DirectAdapter(clients, contracts or week1_contracts()), providers
