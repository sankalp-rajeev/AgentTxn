# Experimental protocol

Status: development feasibility run recorded; final-study conditions are not frozen.

Before final data collection, record:

- Benchmark/scenario version and source commit hash.
- Dependency lockfile and execution environment.
- Invariant definitions and baseline implementation versions.
- Fault schedule families, seeds, and concurrency levels.
- Configuration hashes and success/forbidden-state criteria.
- For LLM studies: provider/model version, temperature, max turns, repetitions,
  token accounting, and cost accounting.
- Raw trace/metric locations and analysis scripts.
- Confidence-interval method, exact counts, and latency sample sizes.

Enumerate deterministic schedules where tractable; otherwise use repeated seeds.
Use at least five independent development runs per LLM condition.
Re-version any final scenario changed after seeing outcomes.

Gate 1 uses scripted agents, not LLM calls. Its intended command is
`python -m experiments.week1_semantic_conflict --seed 42 --baseline all`.
The command is implemented. Gate 1 is REDESIGN; the full study is not authorized
by a successful engineering smoke test alone.

## Week-one development record

- Client date: 16 October 2026.
- Benchmark version: week1-v1; scripted agents, no model or provider costs.
- Implementation commit: 8a71083cbb2eeca59f3ae78ccb8feef084df342a.
- Source-content SHA-256: 7b4b052290958193c4f9b255dca4aca8ea3f6ec63632d85b546ba737f0a952a0.
- Dependency lock SHA-256: e64ecf3c1ed01d9418f68bc3af09489af3aaec4174bf61741f1add6e53fd9539.
- Seed: 42; four scenarios, four baselines, 16 conditions per execution mode.
- Modes: host/memory, host/PostgreSQL, Docker/PostgreSQL. Metric vectors match.
- Host Python: 3.11.14; container Python: 3.11.17; PostgreSQL image: postgres:16.
- Host runs were collected from a clean implementation commit. Docker records
  the identical source-content hash; it has no Git executable.
- Raw evidence: [results/week1](results/week1/README.md).
- Validation: 25 local tests; Ruff; strict mypy; all implementation CI jobs passed
  on Python 3.11/3.12 and Compose/PostgreSQL.
- Each raw trace was reevaluated and checked against its reported metric vector.
- No confidence intervals, statistical rates, or throughput advantage are claimed
  from this single-seed development evaluation.

The initial controlled workload and faults are reproducible; PostgreSQL may
interleave independent completion events. Exact in-memory replay is tested.
