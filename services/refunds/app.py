"""Refund mock API for the cross-service incident compensation invariant."""

from agenttxn.effects.models import Operation
from services.common import MockProvider, create_app

provider = MockProvider(Operation.REFUND)
app = create_app(provider)
