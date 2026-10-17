# Tests

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
