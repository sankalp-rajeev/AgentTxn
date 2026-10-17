# Baselines

Implemented for week one:

- naive.py: immediate execution without admission checks.
- resource_occ.py: read/write version validation over declared raw footprints.
  Write versions are reserved at admission, conservatively invalidating stale
  plans even when provider execution later fails.
- ResourceOCC(semantic_scopes=True): additionally declares a shared incident-budget
  key. This is a stronger metadata control, not a reproduction of a paper.
- AgentTxn uses the semantic certifier, ledger, and reconciliation coordinator.

The shipping OCC read set includes its payment dependency. Both OCC variants
correctly block that stale read; they intentionally have no reconciliation or
replanning strategy in this spike. Do not report their lack of completion as
evidence that OCC cannot be augmented with equivalent recovery.

Serial, idempotency-only, Saga, research-inspired resource frontier, ordered
advisory, and LLM-judge modules remain placeholders.
