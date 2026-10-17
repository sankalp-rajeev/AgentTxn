# Tests

Gate 1B adds outcome-set and evidence-epoch persistence, all seven possible-world
subsets, all five candidate safety classes, matched metadata, all six policies
and four fault schedules, late completion, terminal-abort fencing, capability
checks, exact replay, and a negative control that produces detected violations.
The completed local suite has 45 passing tests with PostgreSQL and TCP enabled.

The suite covers certainty transitions, identity reuse, ambiguous outcomes,
unknown and pending budget reservations, capability-dependent probes, waiting
and wakeup, independent overlap, provider deduplication, PostgreSQL reopen
durability and append-only events, the stronger OCC control, exact in-memory
replay, TCP services, and 30 deterministic Hypothesis budget examples.

Run `uv run --no-sync python -m pytest`. Set AGENTTXN_TEST_DATABASE_URL for the
PostgreSQL test and AGENTTXN_TEST_TCP=1 for the Compose endpoint test; otherwise
they skip explicitly. CI enables both against its own Compose services.

Restricted Windows sessions may need TMP and TEMP pointed at a writable local
directory, for example artifacts/tmp, before running tests.
