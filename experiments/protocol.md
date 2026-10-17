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

## Gate-1B record

- Current direction: AgentTxn_Redesign_Deep_Dive.md, superseding conflicting PRD parts.
- Protocol: gate1b_protocol.md, committed before final result collection.
- Version: gate1b-v1; no LLM APIs or model costs.
- Implementation commit: 6e4d95cd2abcd489e4971641f134d2431cfceda8.
- Source-content SHA-256: 8df55f89fba0a2337110219ec00abe80957ec90fec191d07bb994d7de6a64ba5.
- Dependency lock SHA-256: e64ecf3c1ed01d9418f68bc3af09489af3aaec4174bf61741f1add6e53fd9539.
- Seed 42; two scenarios, eight candidates each, four provider realizations, six policies.
- Four shared evidence rounds; three unresolved checkpoints then a terminal receipt.
- All seven nonempty outcome sets audited: 112 candidate/outcome-set cases per policy.
- All 368 joint-safe subset cases pass, including in-flight continuations.
- Final evidence: 48 conditions each in memory, host/PostgreSQL, and Docker/PostgreSQL.
- All 144 traces replay successfully. Metrics, matched input hashes, concurrent-call counts,
  source hash, dependency hash, and input-document hashes agree across modes.
- Host collections cite a clean implementation commit. Docker cites the identical content hash.
- Validation: 45 local tests passed with PostgreSQL/TCP enabled; Ruff; strict mypy;
  all implementation CI jobs passed on Python 3.11/3.12 and Compose/PostgreSQL.
- Counts are finite feasibility observations, not estimates of arbitrary production rates.
- Modes are reproduction checks, not independent repetitions for confidence intervals.
- Verdict: STOP for AgentTxn as a differentiated runtime; no original Week-2 or LLM build.

Report: [gate1b_uncertainty_containment.md](gate1b_uncertainty_containment.md).
Raw evidence: [results/gate1b](results/gate1b/README.md).
