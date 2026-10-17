# Baselines

Gate-1B matched-information policies are in `uncertainty.py`: global fail-closed,
synthetic-scope OCC, Atomix-inspired scope/frontier, semantic pending-state/lock,
TCT-C-inspired joint recertification, and the reference OCA. All receive the same
complete immutable metadata and evidence, with identical per-round input hashes.
Strong scope/lock controls compile the supplied predicates rather than discarding
their semantic information. Research-inspired names do not imply full paper ports.

The implementations below are preserved Week-1 baselines, not the Gate-1B controls.

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
