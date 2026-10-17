# Experimental protocol

Status: template; no experiments have run and no final conditions are frozen.

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
This command is a placeholder until the spike is implemented.
