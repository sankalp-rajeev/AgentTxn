"""Payment mock API; run with uvicorn services.payments.app:app."""

from agenttxn.effects.models import Operation
from services.common import MockProvider, create_app

provider = MockProvider(Operation.CHARGE)
app = create_app(provider)
