# Week-one feasibility spike

Status: not implemented. This checklist follows PRD sections 46 and 48-49.

- [x] Create repository directories and module placeholders.
- [x] Add Python packaging, Ruff, mypy, pytest configuration, and CI definition.
- [x] Complete targeted Gate 0 check; proceed only with the bounded spike.
- [ ] Implement Payment and Shipping mock APIs.
- [ ] Implement PostgreSQL effect ledger and migrations.
- [ ] Define EffectIntent and the certainty-state model.
- [ ] Add deterministic timeout-after-effect injection.
- [ ] Implement naive and resource OCC baselines.
- [ ] Implement shipment_requires_confirmed_payment.
- [ ] Run two concurrent scripted agents under a lost payment acknowledgement.
- [ ] Add refund/account-credit or another true disjoint-resource semantic conflict.
- [ ] Confirm resource OCC misses it and AgentTxn prevents it.
- [ ] Preserve traces for every condition and report actual metrics.
- [ ] Verify independent work proceeds concurrently.
- [ ] Record GO / REDESIGN / STOP with evidence.

Intended deliverable:

```text
python -m experiments.week1_semantic_conflict --seed 42 --baseline all
```

The deliverable must compare naive, resource_occ, and agenttxn for both ambiguous
payment/shipment and a disjoint-resource conflict. No results exist yet.
