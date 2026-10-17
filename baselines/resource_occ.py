"""Resource-only OCC with optional synthetic semantic scopes as a stronger control."""

from agenttxn.effects.ledger import Ledger
from agenttxn.effects.models import Certification, Decision, EffectIntent


class ResourceOCC:
    def __init__(self, *, semantic_scopes: bool = False) -> None:
        self.semantic_scopes = semantic_scopes
        self.versions: dict[str, int] = {}

    def keys(self, intent: EffectIntent) -> tuple[str, ...]:
        keys = set(intent.resource_footprint) | set(intent.read_versions)
        if self.semantic_scopes and intent.incident_id:
            keys.add(f"incident:{intent.incident_id}:budget")
        return tuple(sorted(keys))

    async def certify(self, intent: EffectIntent, ledger: Ledger) -> Certification:
        keys = self.keys(intent)
        # All plans in the controlled race read their declared resources at version zero.
        if any(self.versions.get(key, 0) != intent.read_versions.get(key, 0) for key in keys):
            return Certification(
                decision=Decision.BLOCK, reason="Declared resource version changed"
            )
        # Reserve write versions during admission, before releasing the key locks.
        writes = set(intent.resource_footprint)
        if self.semantic_scopes and intent.incident_id:
            writes.add(f"incident:{intent.incident_id}:budget")
        for key in writes:
            self.versions[key] = self.versions.get(key, 0) + 1
        return Certification(decision=Decision.COMMIT, reason="Declared resource versions match")
