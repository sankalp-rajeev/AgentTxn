"""Execute immediately with no semantic or resource admission checks."""

from agenttxn.effects.ledger import Ledger
from agenttxn.effects.models import Certification, Decision, EffectIntent


class NaivePolicy:
    def keys(self, intent: EffectIntent) -> tuple[str, ...]:
        return ()

    async def certify(self, intent: EffectIntent, ledger: Ledger) -> Certification:
        return Certification(decision=Decision.COMMIT, reason="Uncoordinated baseline")
