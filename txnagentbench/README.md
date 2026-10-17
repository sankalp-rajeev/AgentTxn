# TxnAgentBench

Week-one Commerce scenarios and runner are implemented. Other domains remain
placeholders and the final benchmark is not frozen.

- schema.py validates the PRD scenario fields.
- commerce/week1.py defines ambiguity twins, a shared compensation budget race,
  and independent-incident work.
- local.py creates separate HTTP providers and retains their truth journals.
- runner.py controls seeded admission and writes per-condition JSONL evidence.
- evaluator.py separates real invariant violations from actions taken without
  confirmed prerequisite evidence.

Run `python -m experiments.week1_semantic_conflict --seed 42 --baseline all`.
Use --ledger postgres for a persistent ledger. Traces include normalized runtime
events and separately ordered provider commit records. The summary preserves
exact scenarios, contracts, faults, configuration hashes, and source provenance.

No LLM calls are made. The synthetic-scope OCC control is required to interpret
the metadata limitation honestly. See experiments/week1.md for the REDESIGN gate.
