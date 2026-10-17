# AgentTxn

AgentTxn is an experimental runtime and benchmark for semantic concurrency in tool-using AI agents. It studies cross-service business invariants when external effects may be ambiguous after timeouts.

**Status: Gate-1B uncertainty-containment feasibility only.** The original Week-2 build remains stopped.
The [redesign deep dive](AgentTxn_Redesign_Deep_Dive.md) is the current research direction and overrides conflicting parts of the [original PRD](AgentTxn_PRD.md).

## Run Gate 1B

```powershell
uv sync --locked --extra dev
uv run --no-sync python -m experiments.gate1b_uncertainty_containment --seed 42 --baseline all
```

Gate 1B compares six equally informed admission policies on payment and cross-workflow refund uncertainty. Each condition has eight scripted concurrent candidates, explicit COMMITTED/ABSENT/IN_FLIGHT possibilities, and shared evidence rounds. Output is written to `artifacts/gate1b/` and replay-verified before reporting.

Use `--ledger postgres` with DATABASE_URL, or `docker compose run --build --rm gate1b`. No LLM APIs are used. Named TCT-C and Atomix policies are bounded research-inspired admission models, not full paper reproductions.

## The failure and the boundary

A charge commits, its acknowledgement is lost, and a concurrent agent requests shipment. AgentTxn records `UNKNOWN`, probes the provider, and admits shipment only after payment is confirmed. The counterfactual timeout-before-effect receives the same error but reconciles to a failed payment and blocks shipment.

A second scenario races a $300 refund against a $300 account credit under a $500 incident budget. AgentTxn includes pending and unknown reservations in its certification view and prevents the excess. Bare resource OCC misses it when its declared footprints are separate.

**Adding a shared incident-budget key to OCC also prevents that conflict.** This is evidence about incomplete conflict metadata, not a demonstrated algorithmic advantage over correctly scoped resource coordination. See the [gate verdict and measured evidence](experiments/week1.md).

## Run the spike

Use Python 3.11+ and uv:

```powershell
uv sync --locked --extra dev
uv run --no-sync python -m experiments.week1_semantic_conflict --seed 42 --baseline all
```

The command compares naive execution, resource OCC, AgentTxn, and resource OCC with a synthetic incident-budget scope. It runs four scenarios: timeout after payment, timeout before payment, disjoint-resource compensation, and independent compensation.

Outputs are `artifacts/week1/summary.json` and one JSONL trace per condition. The manifest records scenarios, contracts, faults, seed, dependency hash, source commit, dirty state, and source-content hash. Provider truth and runtime knowledge are evaluated separately.

## PostgreSQL and Compose

```powershell
Copy-Item .env.example .env
docker compose up -d --build --wait
docker compose run --build --rm benchmark
```

Compose runs PostgreSQL plus Payment, Shipping, Refund, and Customer Credit mock APIs. The benchmark container creates fresh in-process HTTP providers for each condition and uses the real PostgreSQL ledger. Standalone TCP APIs are independently smoke-tested; provider effects themselves are deliberately in memory.

For a host-side persistent run:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://agenttxn:agenttxn_dev@localhost:55432/agenttxn"
uv run --no-sync python -m experiments.week1_semantic_conflict --seed 42 --baseline all --ledger postgres --output artifacts/week1-postgres
```

The example environment uses database port 55432. Without an environment override, Compose defaults to 5432. Each run receives a fresh PostgreSQL namespace; prior audit data is preserved. Migrations apply automatically with checksum validation. Stop the services with `docker compose down`; the database volume persists.

## Verify

```powershell
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy agenttxn txnagentbench baselines services experiments
$env:AGENTTXN_TEST_DATABASE_URL = "postgresql+asyncpg://agenttxn:agenttxn_dev@localhost:55432/agenttxn"
$env:AGENTTXN_TEST_TCP = "1"
uv run --no-sync python -m pytest
```

PostgreSQL and TCP tests skip explicitly when their environment flags are absent. CI runs static checks, bounded property tests, deterministic benchmarks, PostgreSQL integration, and TCP smoke checks. No LLM calls or API keys are required.

## Repository map

- `agenttxn/`: coordination, effects, persistence, contracts, invariants, adapters, and faults.
- `services/`: mock APIs; four Commerce operations are implemented.
- `txnagentbench/`: scenario schema, runner, evaluator, and week-one Commerce cases.
- `baselines/`: naive and resource OCC implementations; later baselines remain placeholders.
- `experiments/`: reproducible week-one command, protocol, and evidence.
- `tests/`: unit, integration, property, and regression coverage.
- `docs/`: [architecture](docs/architecture.md), [literature](docs/literature.md), and [novelty check](docs/novelty.md).
- `artifacts/`: ignored local traces, metrics, and figures.

## Guarantee boundary

The spike supports concurrent tasks behind one coordinator in one process. PostgreSQL persists state but does not make independent coordinator processes safe. External actors bypassing the runtime are not coordinated. Admission locks are released before tool execution; pending and unknown effects reserve semantic capacity.

Negative reconciliation is definitive only because these mocks commit immediately and expose strongly consistent receipts. A missing receipt from a provider with in-flight writes or visibility lag must remain unknown. Capability checks enforce that boundary. Compensation, distributed leadership, crash recovery across provider restarts, additional domains, and LLM integration are not implemented.

AgentTxn does not provide universal atomicity across arbitrary external services. Its guarantees depend on declared tool capabilities and executable invariants. The spike is engineering evidence, not proof of the broader research thesis.

## License and Git workflow

No distribution license has been selected; see [LICENSE](LICENSE).
The repository is [sankalp-rajeev/AgentTxn](https://github.com/sankalp-rajeev/AgentTxn).
Commit and push completed, verified milestones with descriptive messages.
