# Seed-42 feasibility evidence

These are development runs, not a frozen final evaluation. Each ledger mode has
16 conditions: four scenarios crossed with four baselines.

- memory/: seed-42 host run with the in-memory ledger.
- postgres/: seed-42 host run against the local PostgreSQL container.
- docker/: seed-42 container run against PostgreSQL.

Each directory contains summary.json and one JSONL trace per condition. Summaries
record scenario and fault definitions, exact counts, source-content and lockfile
hashes, and source revision when Git is available. Docker has no Git executable;
its source-content hash provides the implementation provenance instead.

Runtime and provider records form separately ordered streams. The evaluator uses
provider commits for physical invariant violations and runtime transitions for
dispatch without a confirmed payment prerequisite. Neither stream substitutes
for the other. Database run identities and wall-clock timestamps are omitted
from exported traces. PostgreSQL may interleave commuting completion events;
in-memory replay is checked byte-for-byte in the regression suite.

The metric vectors agree across all three ledger/execution modes. Synthetic-scope
OCC matches AgentTxn on the budget scenario, so the Gate 1 verdict is REDESIGN.
See [the interpretation](../../week1.md) for the claim boundary.
