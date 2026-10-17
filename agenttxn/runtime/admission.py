"""Common admission-policy boundary shared by the feasibility experiments."""

from typing import Protocol

from agenttxn.effects.ledger import Ledger
from agenttxn.effects.models import Certification, EffectIntent


class AdmissionPolicy(Protocol):
    def keys(self, intent: EffectIntent) -> tuple[str, ...]: ...
    async def certify(self, intent: EffectIntent, ledger: Ledger) -> Certification: ...
