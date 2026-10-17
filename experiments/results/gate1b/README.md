# Gate-1B raw evidence

These are finite feasibility results. Each directory contains the same 48 matched
conditions: two eight-candidate scenarios, four provider realizations, and six
admission policies. The directories are execution/reproduction modes, not extra
independent statistical repetitions.

- memory/: host run using the in-memory ledger.
- postgres/: host run using PostgreSQL.
- docker/: container run using PostgreSQL.

Each contains summary.json and 48 JSONL traces. The summary records exact problem
definitions, tool and compensation capabilities, possible worlds, invariant ASTs,
input-document hashes, source/dependency provenance, input hashes, full metrics,
and the exhaustive decision-equivalence audit.

Traces preserve separate evidence, decision-panel, runtime, provider-commit, and
provider-checkpoint streams. Hidden provider realizations are evaluator-only and
are not part of the policies' shared admission views. Raw evidence is replayed
against the concrete-world oracle and provider prefixes; it does not contact a
database or external service.

All 144 conditions replay successfully and agree across execution modes. Host
runs cite clean implementation commit 6e4d95cd2abcd489e4971641f134d2431cfceda8.
Docker has no Git executable; its identical source-content hash provides the
implementation linkage. PostgreSQL can reorder commuting completion events.

Source-content SHA-256:
8df55f89fba0a2337110219ec00abe80957ec90fec191d07bb994d7de6a64ba5

The conclusion is STOP for a differentiated runtime contribution: TCT-C, synthetic
scopes/frontiers, and semantic pending locks match OCA under the supplied metadata.
See [the complete report](../../gate1b_uncertainty_containment.md).
