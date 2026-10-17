# Architecture and implementation boundary

## Gate-1B additions

The redesign deep dive supersedes the original PRD. Gate 1B reuses the coordinator,
HTTP adapter, ledger, migrations, providers, and provenance. It does not advance
the original Week-2 architecture.

`effects/outcomes.py` separates possible external worlds from the six certainty
states. Additive migrations persist outcome sets and evidence revisions. The
shared admission interface is in `runtime/admission.py`; six Gate-1B policies
consume identical immutable views and validate the same evidence epoch.

`runtime/outcome_admission.py` implements direct OCA; `baselines/uncertainty.py`
implements equally informed controls. Symbolic compatibility compilation is
separate from the benchmark's concrete possible-world oracle. The uncertain
provider extends Week-1 fault injection with late completion and terminal abort;
the receipt API stays the same. Quiescence is an explicit declared capability.

`txnagentbench/uncertainty_runner.py` schedules common evidence rounds and
concurrent candidates. `uncertainty_replay.py` reevaluates raw evidence offline.
`metrics/collateral.py` uses identical fixed decision-panel denominators.

## Preserved Week-1 boundary

The week-one spike implements one coordinator per process, four mock Commerce
operations, two invariants, three principal runtime policies, and an augmented
resource-OCC control. Other scaffold modules remain placeholders.

## Runtime flow

Adapters convert an intent into an HTTP request. The coordinator registers the
intent, locks the relevant admission scopes in sorted order, certifies against
the ledger, and persists PENDING before releasing those locks and dispatching.

Independent scopes can dispatch concurrently. CONFIRMED, PENDING, and UNKNOWN
compensation consume capacity; failed effects do not. Unadmitted NOT_STARTED
proposals are visible but do not reserve budget. This avoids double-counting the
candidate and conservatively blocks oversubscription without rejecting both
proposals merely because both were registered.

Shipment requires confirmed payment. An UNKNOWN prerequisite triggers a
contract-declared probe, followed by reevaluation. Pending prerequisites wait on
a condition notification with a bounded escalation budget; no polling loop is
required. Ambiguous errors and cancellation after admission preserve uncertainty.
Repeated submission of an existing ambiguous effect does not execute it again.

## Modules

- `effects/certainty.py`: six states and legal transitions.
- `effects/models.py`: intents, records, certification decisions, and audit events.
- `effects/ledger.py`: protocol and in-memory reference.
- `effects/postgres.py`: durable implementation and checksum migration runner.
- `effects/migrations/`: versioned schema; state, observation, and event writes
  occur in one PostgreSQL transaction. Event updates/deletes are rejected.
- `contracts/models.py`: capability declarations and HTTP request/outcome models.
- `runtime/coordinator.py`: admission, dispatch, reconciliation, wait/wakeup.
- `runtime/certifier.py` and `invariants/base.py`: week-one business rules.
- `faults/injector.py`: explicit per-operation fault schedules.
- `adapters/direct.py`: HTTP boundary and conservative ambiguous-result handling.

The week-one schema includes transactions, effect_intents, effect_observations,
effect_events, and a migration registry. Transaction lifecycle orchestration,
effect dependency tables, graph storage, benchmark-result tables, and other
planned production data structures are deferred.

## Benchmark and provider truth

Mock providers expose FastAPI endpoints and maintain independent committed-effect
journals. The benchmark uses fresh HTTPX ASGI transports for each condition.
The evaluator checks that provider journal for real unpaid shipments and budget
violations, separately from runtime event evidence for premature downstream
actions. Runtime code cannot query the evaluator's provider journal.

Explicit rendezvous events control the conflicting schedule. A separate
independent-work rendezvous requires two requests to be in flight at once.
The seed controls prepared launch order. In-memory AgentTxn traces replay exactly;
PostgreSQL can interleave commuting completion events differently, while inputs,
faults, admission order, and metrics remain reproducible.

## Boundaries

PostgreSQL row locks protect ledger updates, not distributed admission. Multiple
coordinators or out-of-band provider mutations are not safe under this protocol.
Mock receipts are immediately and strongly consistent; absent receipts may
resolve UNKNOWN only when the declared contract makes absence definitive.
Unknown reservations are retained until evidence resolves them.

Compensation is not implemented. The PRD's COMPENSATING effect-state ambiguity
remains deferred; the six-state certainty enum has not silently gained a state.
There is no global external atomicity or provider-restart recovery guarantee.

Gate 1 is REDESIGN because synthetic-scope OCC prevents the same budget race.
Do not expand to the full architecture without a revised research boundary.
