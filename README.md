# AgentTxn

AgentTxn is an experimental runtime and benchmark for semantic concurrency in tool-using AI agents. It studies cases where concurrent actions touch different services or records but jointly violate a business invariant, especially when external effects may be delayed or ambiguous after timeouts.

**Status: repository scaffold.** Runtime behavior, mock APIs, benchmarks, and results are not implemented. The approved scope is the one-week feasibility spike; the full build remains conditional on the PRD's stop/go gates.

The target failure trace is: a payment commits, its acknowledgement is lost, and a concurrent agent requests shipment. The planned runtime preserves the payment as `UNKNOWN`, reconciles it, and certifies the dependent shipment only when its prerequisite is confirmed. The spike must also demonstrate a disjoint-resource conflict, such as a refund and an account credit exceeding one incident's compensation budget.

## Start here

- [Original PRD](AgentTxn_PRD.md) is the requirements source of truth.
- [Architecture and module boundaries](docs/architecture.md) explains the scaffold.
- [Novelty gate](docs/novelty.md) records the research check required before implementation.
- [Week-one checklist](experiments/week1.md) tracks the first feasibility milestone.
- [Experiment protocol](experiments/protocol.md) will record frozen configurations before final runs.

## Local setup

Use Python 3.11+ and uv:

```powershell
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy agenttxn txnagentbench baselines services experiments
```

Alternatively, create and activate a virtual environment and run `python -m pip install -e ".[dev]"`.

No lockfile is included yet. Generate and commit `uv.lock` when dependency resolution is available; freeze experiment dependencies before collecting results.

## Development infrastructure

Copy `.env.example` to `.env`, then start the development database:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
docker compose exec -T postgres pg_isready -U agenttxn -d agenttxn
docker compose down
```

Compose currently provisions only PostgreSQL. Mock Payment and Shipping APIs, database migrations, and the benchmark runner are future implementation work. Database data persists in a named volume.

## Repository map

- `agenttxn/`: coordination, effect tracking, contracts, executable invariants, faults, adapters, and metrics.
- `services/`: domain mock services, starting with Payments and Shipping.
- `txnagentbench/`: scenario schema, runner, evaluator, and domain scenarios.
- `baselines/`: naive, serial, idempotency, Saga, resource OCC, optional research-inspired approaches, and an LLM judge.
- `experiments/`: the week-one entry point, later studies, and experiment protocol.
- `configs/`: domain configuration placeholders; CloudOps is optional.
- `tests/`: unit, integration, property, and regression test locations.
- `docs/`: architecture, literature, novelty, and protocol guidance.
- `artifacts/`: ignored generated traces, metrics, and figures.

Module docstrings describe ownership; they are not working implementations. Experiment entry points fail explicitly until implemented. CI checks Ruff and typing, runs tests when test files exist, and smoke-checks PostgreSQL. Benchmark smoke coverage must be added with the first runnable scenario.

## Guarantee boundary

AgentTxn does not provide universal atomicity across arbitrary external services. Its guarantees are conditional on declared tool capabilities and executable application invariants. When an external effect cannot be safely reconciled or compensated, the runtime must preserve uncertainty and block dependent consequential actions rather than guessing an outcome.

This is a design requirement, not a demonstrated guarantee of this scaffold.

## License

No distribution license has been selected. See [LICENSE](LICENSE).

## Git workflow

The repository is hosted at [sankalp-rajeev/AgentTxn](https://github.com/sankalp-rajeev/AgentTxn).
Commit and push completed, verified milestones with descriptive commit messages.
