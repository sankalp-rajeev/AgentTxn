# Week-one feasibility spike

Implementation and initial evaluation completed on 16 October 2026.
**Gate 1 verdict: REDESIGN the stronger research claim before a full build.**

## Completed work

- [x] Repository skeleton, locked Python environment, Ruff, typing, pytest, and CI.
- [x] Targeted novelty check with primary sources and bounded conclusions.
- [x] Payment and Shipping mock HTTP APIs.
- [x] Refund and Customer Credit APIs for the disjoint-resource case.
- [x] PostgreSQL ledger, checksum migration, durable observations, append-only events.
- [x] Typed EffectIntent and six-state evidence-based certainty model.
- [x] Deterministic timeout-before-effect and timeout-after-effect injection.
- [x] Naive, resource OCC, and AgentTxn comparison.
- [x] Stronger OCC control with a shared incident-budget key.
- [x] Confirmed-payment prerequisite and active-reservation compensation invariants.
- [x] Two concurrent scripted workflows and reproducible admission scheduling.
- [x] Independent provider calls demonstrably overlap.
- [x] Unit, integration, bounded property, deterministic replay, and TCP checks.
- [x] Docker Compose services and containerized PostgreSQL benchmark reproduction.
- [x] Preserve raw traces and provenance for the development evaluation.
- [x] Record GO / REDESIGN / STOP with evidence.

## Reproduce

```text
uv run --no-sync python -m experiments.week1_semantic_conflict --seed 42 --baseline all
```

Use `--ledger postgres` with DATABASE_URL for persistence, or
`docker compose run --build --rm benchmark` after starting Compose.

## Observed seed-42 development outcomes

The four baseline conditions share scenario definitions, initial versions,
contracts, fault schedules, and controlled admission order.

- Lost acknowledgement after a real charge: naive dispatches shipment without
  confirmed local evidence (one unsafe downstream action), but no physical
  unpaid-shipment violation. Resource OCC blocks its stale payment read.
  AgentTxn reconciles and completes both effects safely.
- Timeout before the charge: naive ships without a real payment (one physical
  violation and one unsafe action). OCC blocks on the changed reservation version
  but leaves the outcome unknown. AgentTxn obtains definitive absence, marks the
  charge FAILED, and blocks shipment.
- Disjoint-resource compensation: naive and bare-footprint OCC commit 60000 cents
  against a 50000-cent budget (one violation). AgentTxn and synthetic-scope OCC
  each admit one 30000-cent effect, with zero budget violations.
- Independent incidents: all baselines admit both effects and reach two provider
  requests in flight. This proves overlap in the controlled schedule, not a
  throughput improvement or statistical speedup.

The PostgreSQL run matches the in-memory metrics. The benchmark also runs inside
Docker with a real PostgreSQL ledger. See the committed raw evidence under
[results/week1](results/week1/README.md).

## Gate interpretation

The bare-resource counterexample is real under its declared footprints, but the
synthetic incident key repairs the same case with ordinary OCC. A shared budget
lock can do so as well. Therefore the stronger claim that this example escapes
resource coordination does not pass the PRD's Gate 1 reduction check.

The payment result supports the usefulness of uncertainty-aware reconciliation
relative to these specific baselines. It does not establish novelty over prior
systems or an OCC baseline augmented with equivalent reconciliation.

Stop the full-build progression here. A revised study would need a justified
distinction in uncertainty propagation, capability-dependent admission, dynamic
semantic dependencies, or an independently valuable benchmark, and stronger
controls with matched information and recovery capabilities.

These are development feasibility results, not frozen final-study results.
No model experiments, second domain, compensation path, full fault matrix,
distributed correctness claim, or throughput claim is included.
