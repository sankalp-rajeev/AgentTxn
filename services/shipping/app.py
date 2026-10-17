"""Shipping mock API; run with uvicorn services.shipping.app:app."""

from agenttxn.effects.models import Operation
from services.common import MockProvider, create_app

provider = MockProvider(Operation.SHIP)
app = create_app(provider)
