# AgentTxn — Product / Research Requirements Document

**Version:** 1.0  
**Date:** 16 October 2026  
**Status:** Approved for a one-week feasibility spike; full build is conditional on the stop/go gates in this document.  
**Project type:** Research-engineering flagship project  
**Working title:** **AgentTxn**  
**Subtitle:** Semantic concurrency control for tool-using AI agents under uncertain external effects

---

# 1. Executive summary

Modern LLM agents increasingly perform real actions through APIs: charging customers, issuing refunds, reserving inventory, changing permissions, deploying services, sending messages, and modifying databases.

The problem is that current agent stacks often treat each tool call like a clean, isolated RPC. Real systems are not clean:

- multiple agents can act at the same time,
- reads can be stale,
- an API can time out after the real-world action already happened,
- retries can duplicate irreversible effects,
- compensation can fail,
- two individually valid actions on different resources can jointly violate a business rule,
- external services do not share one global transaction manager.

Existing research already covers important subsets: Saga-style recovery, replay, idempotency, task-level transactions, resource-level concurrency control, shared-memory transactions, and duplicate-effect handling. Therefore AgentTxn must **not** claim generic “transactions for agents” as its contribution.

The narrowed project studies:

> **Can explicit semantic invariants and uncertainty-aware effect tracking preserve cross-service correctness for multiple concurrent AI agents when raw resource overlap is not enough to detect conflicts?**

AgentTxn will contribute two tightly connected artifacts:

1. **AgentTxn Runtime** — a runtime that tracks effect certainty, evaluates executable cross-service invariants, and decides whether an action may commit, must wait, should reconcile, should compensate, requires replanning, or must escalate to a human.
2. **TxnAgentBench** — a reproducible benchmark for concurrent tool-using agents under stale reads, ambiguous timeouts, delayed commits, duplicate delivery, partial failures, semantic conflicts, and irreversible effects.

The system is successful only if it demonstrates a measurable result that resource-level or retry-only baselines miss.

---

# 2. Problem statement

Tool-using LLM agents operate over heterogeneous external services that have different consistency and failure semantics.

Consider two agents:

- Agent A charges a customer.
- The payment provider completes the charge, but the response is lost.
- AgentTxn therefore knows only that the payment outcome is **UNKNOWN**.
- At the same time, Agent B tries to ship the order.

A naive system may retry the charge, ship before payment is confirmed, or allow another agent to make a conflicting financial decision.

The core problem is deeper than duplicate retries:

> **Concurrent actions can be semantically incompatible even when they touch different rows, APIs, or service objects.**

Example:

- Agent A issues a $300 refund on one order.
- Agent B issues a $300 account credit through another service.
- Each action is individually valid.
- They touch different records.
- The business invariant says total discretionary compensation for the incident cannot exceed $500.
- The combined state is invalid.

Traditional read/write conflict detection may miss this because the conflict exists at the level of **business meaning**, not a shared record key.

---

# 3. Research thesis

> **AgentTxn studies whether explicit semantic invariants and uncertainty-aware effect tracking can provide practical isolation for concurrent AI agents across heterogeneous APIs when ordinary resource-level transactions are not enough.**

---

# 4. Primary research question

> **RQ1:** Can semantic commit certification reduce cross-service invariant violations in concurrent tool-using LLM agents under retries, stale state, and ambiguous external outcomes while preserving useful parallelism?

Secondary questions:

- **RQ2:** How much correctness is lost when conflict detection uses only raw resource overlap rather than semantic invariants?
- **RQ3:** How much does representing `UNKNOWN` as a first-class effect state reduce duplicate or invalid downstream actions?
- **RQ4:** What latency and throughput cost does semantic commit certification add compared with unrestricted execution and fully serial execution?
- **RQ5:** Which guarantees fail when tool contracts omit reconciliation, idempotency, or compensation capabilities?
- **RQ6:** How sensitive is correctness to missing or incorrectly specified invariants?

---

# 5. Hypotheses

These are pre-registered hypotheses, not claims.

### H1 — Semantic conflicts
Resource-overlap-only concurrency control will miss conflicts constructed over disjoint resources that share a higher-level business invariant.

### H2 — UNKNOWN matters
Explicitly representing `UNKNOWN` will reduce duplicate and invalid downstream actions relative to treating timeout as either success or failure.

### H3 — Runtime correctness
Semantic commit certification will reduce invariant violations relative to naive, idempotency-only, Saga-only, and resource-level concurrency baselines.

### H4 — Parallelism
AgentTxn will preserve materially more useful parallelism than fully serial execution.

### H5 — Tool contracts matter
Incorrect or incomplete tool metadata will remain an important residual failure source.

### H6 — LLM judgment is insufficient
A deterministic invariant layer will outperform an LLM-only conflict judge on reproducibility and violation rate under adversarial/faulted scenarios.

---

# 6. Non-goals

AgentTxn is **not**:

- a universal distributed transaction system for arbitrary SaaS products,
- a replacement for PostgreSQL transactions,
- a two-phase-commit protocol across the Internet,
- a generic multi-agent framework,
- a policy compiler from natural language,
- an LLM guardrail project,
- a prompt-injection defense,
- an RL project,
- a model-training project,
- a Kubernetes platform,
- a frontend/dashboard project,
- a claim of global atomicity across irreversible external effects.

The system must be explicit about what it can and cannot guarantee.

---

# 7. Literature-driven scope boundary

The following areas are considered prior-art territory and therefore cannot be the main novelty claim:

- Saga-style recovery and compensation,
- idempotency and duplicate suppression,
- deterministic replay,
- task-level transaction staging,
- resource-level concurrency control,
- shared-memory transactional commit,
- exactly-once-style retry protection,
- generic “ACID for agents,”
- generic “semantic transactions,”
- generic “concurrency control for agents.”

AgentTxn's candidate contribution is the **combination** of:

1. multiple concurrent agent workflows,
2. heterogeneous external services,
3. semantic business invariants spanning non-overlapping resources,
4. explicit in-doubt / `UNKNOWN` external effects,
5. online commit decisions using those invariants,
6. dynamic agent activity rather than only a fixed launch order,
7. fault injection covering delayed and ambiguous effects,
8. concurrency-aware evaluation,
9. measured correctness vs useful parallelism.

If a newly discovered system already provides nearly all nine, the project must be redesigned.

---

# 8. Product concept

AgentTxn sits between the agent runtime and side-effecting tools.

```text
      Agent A ──────┐
      Agent B ──────┼────> AgentTxn Runtime ─────> External Tools / APIs
      Agent C ──────┘              |
                                   |
                        ┌──────────┴──────────┐
                        |                     |
                Effect Ledger        Semantic Invariants
                        |                     |
                        └──────────┬──────────┘
                                   |
                           Commit Certifier
                                   |
          ┌───────────┬────────────┼────────────┬──────────────┐
          |           |            |            |              |
       COMMIT        WAIT      RECONCILE    COMPENSATE      REPLAN
                                                         / HUMAN REVIEW
```

The LLM proposes actions.

**The LLM does not decide whether its own consequential action is safe to commit.**

The commit boundary is deterministic.

---

# 9. Core abstractions

## 9.1 Transaction

A logical unit of agent work.

```python
Transaction:
    transaction_id
    agent_id
    workflow_id
    start_time
    status
    intents[]
    reads[]
    effects[]
    dependencies[]
```

Possible statuses:

```text
ACTIVE
WAITING
RECONCILING
COMMITTED
COMPENSATING
ABORTED
NEEDS_REVIEW
```

---

## 9.2 Effect intent

Before an external action executes, the agent creates an `EffectIntent`.

```python
EffectIntent:
    effect_id
    logical_operation_id
    transaction_id
    agent_id

    tool_name
    operation_name
    arguments

    semantic_tags
    resource_footprint

    preconditions
    expected_postconditions

    reversibility_class
    idempotency_capability
    reconciliation_capability
    compensation_capability

    certainty_state
    dependencies

    created_at
    updated_at
```

---

## 9.3 Effect certainty state

Every consequential effect must have one of these states:

```text
NOT_STARTED
PENDING
CONFIRMED
FAILED
UNKNOWN
COMPENSATED
```

### Key rule

`UNKNOWN` is not equivalent to either `FAILED` or `CONFIRMED`.

A timeout after submitting an external request may result in:

```text
local observation = timeout
real-world outcome = success
```

The runtime must preserve this uncertainty until reconciliation proves the actual state.

---

## 9.4 Reversibility class

Each tool operation declares one of:

```text
REVERSIBLE
COMPENSATABLE
IRREVERSIBLE
```

Examples:

```text
update_draft_record       -> REVERSIBLE
issue_refund              -> COMPENSATABLE (domain-dependent)
send_external_email       -> IRREVERSIBLE
publish_dns_change        -> COMPENSATABLE / delayed
ship_package              -> IRREVERSIBLE after carrier acceptance
```

This metadata is part of the tool contract.

---

## 9.5 Tool contract

Every side-effecting operation exposes a machine-readable contract.

Example:

```yaml
tool: payment_service
operation: charge

effect_class: compensatable

idempotency:
  supported: true
  key_field: logical_operation_id

reconciliation:
  supported: true
  operation: get_charge_status

compensation:
  supported: true
  operation: refund_charge

resource_footprint:
  - "payment:{order_id}"

semantic_tags:
  - payment
  - financial_commitment
```

AgentTxn must never pretend to guarantee exactly-once or rollback semantics when the tool does not expose sufficient capabilities.

---

# 10. Semantic invariants

Semantic invariants are deterministic developer-authored rules describing end-to-end business correctness.

Natural-language-to-policy compilation is explicitly out of scope for the research contribution.

The first version should support Python functions plus optional declarative metadata.

Example:

```python
@invariant("shipment_requires_confirmed_payment")
def shipment_requires_confirmed_payment(state, intent):
    if intent.operation_name != "ship_order":
        return PASS

    payment = state.payment_status(intent.arguments["order_id"])

    if payment == CONFIRMED:
        return PASS

    if payment in {PENDING, UNKNOWN}:
        return WAIT

    return BLOCK
```

Another:

```python
@invariant("incident_compensation_cap")
def incident_compensation_cap(state, intent):
    if "customer_compensation" not in intent.semantic_tags:
        return PASS

    incident = intent.arguments["incident_id"]

    projected_total = (
        state.committed_compensation(incident)
        + state.active_compensation_intents(incident)
        + intent.arguments["amount"]
    )

    return PASS if projected_total <= 500 else BLOCK
```

The important property is that the invariant may reference **several services and several active transactions**.

---

# 11. Semantic Effect Graph

AgentTxn maintains a graph of intended, observed, and committed effects.

Node:

```text
EffectIntent / EffectObservation / ExternalEffect
```

Edges:

```text
DEPENDS_ON
MAY_CONFLICT_WITH
COMPENSATES
DERIVED_FROM
MUST_PRECEDE
RECONCILES
```

The graph allows the runtime to ask:

- Is this intent dependent on an unresolved effect?
- Does another active transaction consume the same semantic budget/capacity?
- Would both intents jointly violate an invariant?
- Is a compensation in progress?
- Is a prerequisite merely missing or truly failed?
- Can this intent commit independently?

The graph is not intended to be a general knowledge graph.

It is an execution structure.

---

# 12. Semantic commit certification

Before a consequential action commits, the certifier builds a certification view from:

- committed effects,
- active intents,
- unresolved `UNKNOWN` effects,
- relevant external state,
- tool capabilities,
- dependency graph,
- invariants,
- reversibility metadata.

Possible decisions:

```text
COMMIT
WAIT
RECONCILE
COMPENSATE
REPLAN
BLOCK
HUMAN_REVIEW
```

Example:

```text
payment(order=123) = UNKNOWN
ship(order=123) requested
```

Invariant:

```text
ship(order) requires payment(order) == CONFIRMED
```

Decision:

```text
RECONCILE payment(123)
then reevaluate
```

Not:

```text
assume failed and retry payment
```

Not:

```text
assume success and ship
```

---

# 13. Runtime execution protocol

High-level flow:

```text
1. Agent proposes tool call.
2. Adapter converts call into EffectIntent.
3. Runtime registers intent in ledger.
4. Certifier identifies relevant invariants.
5. Runtime evaluates:
   a. current state
   b. other active intents
   c. unresolved effects
   d. dependency graph
6. Runtime returns decision.

If COMMIT:
   7. mark PENDING
   8. execute tool
   9. record observation

If success:
   10. mark CONFIRMED

If definite failure:
   10. mark FAILED

If ambiguous:
   10. mark UNKNOWN
   11. enqueue reconciliation

12. Reevaluate blocked/dependent transactions whenever relevant state changes.
```

---

# 14. Reconciliation protocol

For an `UNKNOWN` effect:

```text
1. Do not blindly retry.
2. Check tool contract.
3. If reconciliation probe exists:
      query provider truth.
4. If provider confirms effect:
      UNKNOWN -> CONFIRMED
5. If provider confirms non-effect:
      UNKNOWN -> FAILED
6. If still unresolved:
      remain UNKNOWN
      block dependent irreversible actions
      optionally escalate after timeout budget
```

Idempotent retry is allowed only when the tool contract says the retry is safe.

---

# 15. Compensation protocol

Compensation is not rollback.

For compensatable effects:

```text
original effect = CONFIRMED
workflow later invalidates
runtime invokes declared compensating operation
```

Possible state:

```text
CONFIRMED -> COMPENSATING -> COMPENSATED
```

If compensation fails:

```text
NEEDS_REVIEW
```

The benchmark must treat compensation failure as a first-class scenario.

---

# 16. Concurrency strategy

The runtime must **not** globally serialize all transactions.

Independent intents should execute concurrently.

Blocking occurs only when:

- an invariant says two operations semantically conflict,
- an unresolved effect is a prerequisite for another consequential action,
- the tool contract cannot safely support progress,
- a compensation/reconciliation dependency is active.

The system should maximize useful parallelism subject to invariant preservation.

---

# 17. Benchmark: TxnAgentBench

TxnAgentBench is a required artifact, not optional polish.

It evaluates:

- concurrency,
- ambiguous outcomes,
- stale observations,
- retries,
- duplicate delivery,
- cross-service invariants,
- irreversible effects,
- compensation,
- agent crashes,
- dynamic agent arrival.

Each benchmark scenario must include:

```yaml
scenario_id:
domain:
initial_state:
agents:
workflows:
tool_contracts:
semantic_invariants:
fault_schedule:
success_conditions:
forbidden_states:
expected_serial_outcome:
```

---

# 18. Domain A — Commerce

Services:

- Orders
- Inventory
- Payments
- Shipping
- Refunds
- Customer Credit

Example invariants:

```text
ship(order) =>
payment(order) == CONFIRMED
```

```text
sum(committed_inventory_promises(sku, region, date))
<= available_inventory(sku, region, date)
```

```text
refund(order, incident)
+ account_credit(customer, incident)
<= compensation_budget(incident)
```

Core scenarios:

1. charge succeeds but acknowledgement is lost; concurrent shipment begins,
2. two agents reserve logically shared capacity through different inventory objects,
3. refund and account credit race through separate services,
4. duplicate refund request after agent restart,
5. shipment occurs while compensation/reversal is unresolved,
6. stale inventory read leads to competing commitments,
7. payment confirmation is eventually consistent.

---

# 19. Domain B — Identity / Enterprise SaaS

Services:

- Identity Provider
- Document Service
- Email
- Ticketing
- Approval Service
- Audit Log

Example invariants:

```text
revoked(user) =>
no new protected-resource access may be granted
```

```text
privilege_escalation(user) =>
approval(ticket) == CONFIRMED
```

```text
external_delivery(sensitive_data) =>
approval == CONFIRMED
```

Core scenarios:

1. access revocation races with document sharing,
2. role change races with privileged action,
3. approval API commits but times out,
4. stale directory membership grants access,
5. external email cannot be recalled after commit,
6. approval is cancelled while another agent acts on stale approval state.

---

# 20. Domain C — Cloud Operations

Services:

- Deployment API
- DNS
- Secret Manager
- Load Balancer
- Monitoring

Example invariants:

```text
production_traffic(version) =>
healthcheck(version) == PASS
```

```text
secret_revoked(key) =>
no new deployment may reference key
```

```text
rollback(version) =>
traffic must not remain on failed version
```

Core scenarios:

1. deployment succeeds but response is lost,
2. deploy and rollback occur concurrently,
3. delayed health check races with traffic shift,
4. stale secret metadata allows unsafe deployment,
5. DNS update partially propagates,
6. monitoring result is delayed while another agent promotes traffic.

---

# 21. Fault model

The benchmark must support deterministic injection of:

1. timeout before effect,
2. timeout after effect,
3. delayed commit,
4. lost acknowledgement,
5. duplicated delivery,
6. partial batch success,
7. eventually consistent read,
8. stale read,
9. compensation failure,
10. reconciliation unavailable,
11. concurrent semantic conflict,
12. agent crash,
13. agent restart,
14. tool server crash,
15. reordered observations,
16. dynamic agent spawning,
17. duplicate agent task delivery,
18. delayed dependency notification.

Faults must be reproducible from a seed.

---

# 22. Agent configurations

At minimum evaluate:

### A0 — Scripted deterministic agents
Purpose:
- isolate runtime correctness from LLM randomness.

### A1 — Single LLM agent per workflow
Purpose:
- measure realistic tool behavior.

### A2 — Multiple concurrently running LLM agents
Purpose:
- main project setting.

Use one primary provider/model for MVP.

Add another model/provider only after the benchmark works.

Do not turn provider comparison into the project.

---

# 23. Baselines

## B0 — Naive runtime

Tool calls execute immediately.

No coordination.

---

## B1 — Fully serial execution

Only one workflow may execute consequential effects at a time.

This serves as the conservative correctness oracle.

Expected:

- low concurrency,
- high correctness.

---

## B2 — Idempotency-only

Stable logical operation IDs.

Duplicate suppression when tool supports idempotency.

No semantic invariant coordination.

---

## B3 — Saga compensation

Workflows execute, then compensate on failure.

No semantic concurrent isolation.

---

## B4 — Resource OCC

Track read/write versions.

Conflict only on overlapping declared resources.

This baseline is essential because AgentTxn's central claim is that semantic conflicts can exist without raw overlap.

---

## B5 — Resource-frontier baseline

Implement an Atomix-inspired simplified resource-level commit frontier if feasible.

Do not claim to reproduce the full paper unless implementation fidelity is verified.

---

## B6 — Ordered advisory concurrency

Implement a CoAgent-inspired simplified fixed-order baseline if feasible.

Again, label it clearly as inspired unless faithfully reproduced.

---

## B7 — LLM conflict judge

Ask an LLM whether the proposed action conflicts with active actions.

This tests whether deterministic invariants are necessary.

---

## B8 — AgentTxn

Semantic invariants + effect certainty + online commit certification + reconciliation.

---

# 24. Metrics

## 24.1 Correctness

Primary:

- invariant violation rate,
- unsafe downstream action rate,
- end-state correctness.

Secondary:

- duplicate side-effect rate,
- orphan-effect rate,
- unresolved `UNKNOWN` rate,
- inconsistent cross-service state rate.

---

## 24.2 Concurrency

- tasks completed per minute,
- total wall-clock completion time,
- average runnable agents,
- blocked time,
- wait ratio,
- useful parallelism,
- semantic conflict rate,
- false-conflict / unnecessary-block rate.

---

## 24.3 Recovery

- reconciliation success rate,
- mean time to resolve UNKNOWN,
- compensation success rate,
- duplicate retries prevented,
- human-review rate.

---

## 24.4 Agent cost

- model tokens,
- tool calls,
- replans,
- repeated reasoning steps,
- provider API cost.

---

## 24.5 Runtime overhead

- p50/p95 certification latency,
- invariant evaluation latency,
- ledger write overhead,
- reconciliation overhead,
- total runtime overhead vs naive baseline.

---

# 25. Primary success criteria

The project counts as a successful flagship result only if the final evaluation demonstrates all of the following:

### S1 — Resource-level miss
At least one realistic benchmark class where resource OCC/versioning does not identify a conflict but a semantic invariant does.

### S2 — UNKNOWN value
At least one realistic fault class where collapsing `UNKNOWN` into `FAILED` or `CONFIRMED` creates a measurable correctness regression.

### S3 — Correctness improvement
AgentTxn reduces invariant violations relative to at least:

- naive runtime,
- idempotency-only,
- Saga-only,
- resource OCC.

### S4 — Preserved parallelism
AgentTxn completes concurrent workloads materially faster than fully serial execution while maintaining similar correctness.

### S5 — Generality
The effect is demonstrated in at least two domains.

The third domain is desirable but not necessary if the first two are rigorous.

---

# 26. Stop / go gates

## Gate 0 — Novelty check

Before implementation:

- re-run targeted searches for newest work,
- specifically search for:
  - semantic concurrency LLM agents,
  - cross-service invariants agents,
  - uncertain effect concurrency,
  - semantic serializability agents,
  - in-doubt transaction LLM,
  - multi-agent external side effects.

**Kill condition:** a paper already demonstrates nearly the same nine-part contribution set.

---

## Gate 1 — One-week semantic-conflict spike

Build:

- Payment service,
- Shipping service,
- two concurrent scripted agents,
- effect ledger,
- one invariant,
- one ambiguity fault.

Scenario:

```text
Agent A:
charge(order=123)

provider:
charge commits
response is lost

runtime:
payment(123) = UNKNOWN

Agent B:
ship(order=123)
```

Invariant:

```text
ship(order) requires payment(order) == CONFIRMED
```

Then add one true disjoint-resource semantic conflict.

**Go only if**:

- naive/resource-only baseline fails,
- AgentTxn invariant prevents the failure,
- the scenario is not trivially equivalent to a normal shared row lock.

---

## Gate 2 — Parallelism check

Create independent workloads plus conflicting workloads.

**Go only if** AgentTxn allows independent work to proceed concurrently rather than degenerating into global serialization.

---

## Gate 3 — LLM integration

Only after the deterministic runtime works:

- integrate one LLM tool-calling agent,
- verify that runtime guarantees still hold despite stochastic plans.

Do not debug LLM behavior and transaction semantics simultaneously in Week 1.

---

# 27. Ablations

Required:

### A1 — Remove semantic invariants
Use resource overlap only.

### A2 — `UNKNOWN -> FAILED`
Treat timeout as failure.

### A3 — `UNKNOWN -> CONFIRMED`
Treat timeout as success.

### A4 — No effect graph
Evaluate each call independently.

### A5 — Serial execution
No concurrency.

### A6 — No reconciliation
Retry or compensate only.

### A7 — LLM-only conflict judge
No deterministic final invariant decision.

### A8 — Remove active intents from invariant view
Evaluate only committed state.

This tests whether conflicts must be detected before both effects commit.

### A9 — Incomplete tool metadata
Remove idempotency/reconciliation capability from some tools.

This measures the guarantee degradation caused by weak tool contracts.

---

# 28. Experimental protocol

Before final runs, freeze:

- benchmark scenarios,
- fault schedule families,
- random seeds,
- agent model,
- temperature,
- max turns,
- invariant definitions,
- baseline implementations,
- success criteria.

Do not modify final test scenarios after observing results unless the experiment is explicitly re-versioned.

Maintain:

```text
experiments/protocol.md
```

with:

- benchmark version,
- commit hash,
- provider/model version,
- seeds,
- config hashes.

---

# 29. Statistical methodology

For deterministic scripted workloads:

- enumerate all defined fault schedules where tractable,
- otherwise run multiple seeded repetitions.

For LLM workloads:

- at least 5 independent seeds/runs per condition for development,
- increase final repetitions where cost permits,
- report confidence intervals for primary rates,
- report raw counts alongside percentages,
- do not report only best seed.

Latency:

- p50,
- p95,
- p99 where sample count supports it.

Correctness:

- exact violation counts,
- violation rate,
- confidence interval.

---

# 30. Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                         Agent Layer                           │
│        Agent A              Agent B              Agent C      │
└──────────┬────────────────────┬────────────────────┬───────────┘
           │                    │                    │
           └────────────────────┼────────────────────┘
                                │
                                v
┌───────────────────────────────────────────────────────────────┐
│                      Tool Adapter Layer                       │
│     converts requested tool calls into typed EffectIntent    │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                v
┌───────────────────────────────────────────────────────────────┐
│                       AgentTxn Runtime                        │
│                                                               │
│  Coordinator                                                  │
│      │                                                        │
│      ├──> Semantic Effect Graph                               │
│      ├──> Effect Ledger                                       │
│      ├──> Invariant Registry                                  │
│      ├──> Tool Contract Registry                              │
│      │                                                        │
│      v                                                        │
│  Commit Certifier                                             │
│      │                                                        │
│      ├── COMMIT                                               │
│      ├── WAIT                                                 │
│      ├── RECONCILE                                            │
│      ├── COMPENSATE                                           │
│      ├── REPLAN                                               │
│      └── HUMAN_REVIEW                                         │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                v
┌───────────────────────────────────────────────────────────────┐
│                     Service / Tool Layer                      │
│ Payment | Inventory | Shipping | Identity | Documents | Cloud │
└───────────────────────────────────────────────────────────────┘
```

---

# 31. Data layer

Use PostgreSQL for persistent runtime state.

Core tables:

```text
transactions
effect_intents
effect_observations
effect_dependencies
effect_events
tool_contracts
scenario_runs
benchmark_results
```

An append-only event table should preserve:

```text
timestamp
transaction_id
effect_id
event_type
previous_state
new_state
reason
external_observation
```

The implementation should preserve deterministic replay of the benchmark runtime where possible, but replay itself is not the novelty.

---

# 32. Suggested technology stack

Core:

- Python 3.11+
- FastAPI
- asyncio
- PostgreSQL
- SQLAlchemy or SQLModel
- Pydantic
- pytest
- Hypothesis for property-based tests
- Docker Compose
- Ruff
- mypy or Pyright
- GitHub Actions

Agent layer:

- direct tool-calling adapter first,
- optional LangGraph adapter second.

LLM providers:

- one provider for initial integration,
- optional OpenAI / Anthropic / local adapter later.

Experiment tracking:

- MLflow if it improves reproducibility,
- otherwise structured Parquet/JSON + scripts is acceptable.

Plots:

- Matplotlib.

---

# 33. Repository structure

```text
agenttxn/
├── README.md
├── LICENSE
├── pyproject.toml
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── docs/
│   ├── PRD.md
│   ├── literature.md
│   ├── novelty.md
│   ├── protocol.md
│   └── architecture.md
│
├── configs/
│   ├── commerce.yaml
│   ├── identity.yaml
│   └── cloudops.yaml
│
├── agenttxn/
│   ├── runtime/
│   │   ├── coordinator.py
│   │   ├── certifier.py
│   │   ├── scheduler.py
│   │   ├── reconciliation.py
│   │   └── recovery.py
│   │
│   ├── effects/
│   │   ├── models.py
│   │   ├── certainty.py
│   │   ├── graph.py
│   │   └── ledger.py
│   │
│   ├── contracts/
│   │   ├── models.py
│   │   ├── registry.py
│   │   └── validation.py
│   │
│   ├── invariants/
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── evaluator.py
│   │
│   ├── faults/
│   │   ├── injector.py
│   │   ├── timeouts.py
│   │   ├── delayed_commit.py
│   │   ├── stale_read.py
│   │   └── redelivery.py
│   │
│   ├── adapters/
│   │   ├── base.py
│   │   ├── direct.py
│   │   └── langgraph.py
│   │
│   └── metrics/
│       ├── correctness.py
│       ├── concurrency.py
│       ├── recovery.py
│       └── cost.py
│
├── services/
│   ├── payments/
│   ├── inventory/
│   ├── shipping/
│   ├── identity/
│   ├── documents/
│   └── cloudops/
│
├── txnagentbench/
│   ├── schema.py
│   ├── runner.py
│   ├── evaluator.py
│   ├── commerce/
│   ├── identity/
│   └── cloudops/
│
├── baselines/
│   ├── naive.py
│   ├── serial.py
│   ├── idempotency.py
│   ├── saga.py
│   ├── resource_occ.py
│   ├── resource_frontier.py
│   └── llm_judge.py
│
├── experiments/
│   ├── semantic_conflicts.py
│   ├── unknown_effects.py
│   ├── fault_matrix.py
│   ├── concurrency_scaling.py
│   ├── metadata_ablation.py
│   └── final_study.py
│
└── tests/
    ├── unit/
    ├── integration/
    ├── property/
    └── regression/
```

---

# 34. Testing strategy

## Unit tests

Test:

- certainty-state transitions,
- invariant lookup,
- invariant decision semantics,
- tool-contract validation,
- effect-graph edges,
- reconciliation decisions,
- compensation decisions.

---

## Integration tests

Test:

```text
agent intent
-> certifier
-> tool call
-> injected fault
-> observation
-> certainty transition
-> dependent transaction wakeup
-> invariant reevaluation
```

---

## Property-based tests

Examples:

### P1
No `IRREVERSIBLE` dependent action may commit while a required prerequisite is `UNKNOWN`.

### P2
Committed state must satisfy all hard invariants.

### P3
Idempotent retry must not create multiple confirmed logical effects.

### P4
Two independent transactions should not block each other solely because they are concurrent.

### P5
A compensated effect must not be counted as active committed capacity.

---

## Regression tests

Every discovered correctness bug becomes a permanent regression test.

---

# 35. CI

GitHub Actions:

- Ruff
- type checking
- unit tests
- integration tests
- property tests with bounded examples
- Docker Compose smoke test
- deterministic benchmark smoke scenario

Do not run expensive LLM experiments in CI.

---

# 36. Observability

Each runtime decision should emit structured data:

```text
run_id
transaction_id
agent_id
effect_id
tool
operation
decision
certainty_state_before
certainty_state_after
relevant_invariants
blocking_effect_ids
reconciliation_attempts
latency_ms
timestamp
```

This is needed for:

- debugging,
- benchmark analysis,
- reproducibility,
- failure attribution.

---

# 37. Experiment 1 — Does semantic conflict exist beyond resource conflict?

Construct scenarios where:

```text
resource(A) != resource(B)
```

but:

```text
invariant(A + B) == false
```

Compare:

- resource OCC,
- AgentTxn.

Primary result:

```text
semantic-conflict recall
false block rate
invariant violations
```

This is the most important experiment.

---

# 38. Experiment 2 — UNKNOWN effect handling

Fault schedule:

```text
effect commits externally
acknowledgement lost
runtime sees timeout
```

Compare:

- timeout -> failure,
- timeout -> success,
- immediate retry,
- idempotency-only,
- AgentTxn UNKNOWN + reconciliation.

Measure:

- duplicates,
- invalid dependent actions,
- resolution latency,
- successful workflow completion.

---

# 39. Experiment 3 — Correctness vs concurrency

Vary concurrent transactions:

```text
1
2
4
8
16
32
```

depending on local feasibility.

Compare:

- fully serial,
- naive concurrent,
- resource OCC,
- AgentTxn.

Plot:

```text
invariant violations vs throughput
```

The desired result is not “maximum throughput.”

It is a better correctness/parallelism tradeoff.

---

# 40. Experiment 4 — Fault matrix

Cross:

```text
fault type
x baseline
x concurrency
x domain
```

Measure:

- violation rate,
- recovery rate,
- wall-clock time,
- external side effects.

---

# 41. Experiment 5 — Tool capability ablation

Remove capabilities one at a time:

```text
no idempotency
no reconciliation
no compensation
incomplete resource footprint
incorrect semantic tag
```

Goal:

show which guarantees are possible under which tool contracts.

This experiment prevents the project from making impossible claims about black-box APIs.

---

# 42. Experiment 6 — LLM agent behavior

After runtime correctness is established, replace scripted planners with an LLM tool-calling agent.

Measure whether:

- agents retry incorrectly,
- agents replan around waits,
- agents produce more invalid intents under faults,
- runtime correctness is robust to stochastic plans.

The LLM should stress the runtime, not define the runtime's correctness.

---

# 43. Experiment 7 — Generalization across domains

Train nothing unless necessary.

The core runtime should work by configuration.

Demonstrate the same protocol in:

- Commerce,
- Identity / SaaS,

and optionally:

- CloudOps.

The result should show that the semantic invariant mechanism is not hardcoded to one domain.

---

# 44. Required final plots

1. **Invariant violation rate by baseline**
2. **Throughput vs invariant violation rate**
3. **Violation rate vs concurrency**
4. **Blocked time vs concurrency**
5. **UNKNOWN-resolution outcomes**
6. **Duplicate side effects by timeout policy**
7. **False-conflict rate by baseline**
8. **Certification latency distribution**
9. **Correctness under tool-capability ablations**
10. **Per-domain baseline comparison**

---

# 45. Required final tables

## Table A — Main benchmark

| Baseline | Invariant Violations | Task Success | Throughput | p95 Runtime Overhead | Duplicate Effects |
|---|---:|---:|---:|---:|---:|
| Naive | TBD | TBD | TBD | TBD | TBD |
| Serial | TBD | TBD | TBD | TBD | TBD |
| Idempotency | TBD | TBD | TBD | TBD | TBD |
| Saga | TBD | TBD | TBD | TBD | TBD |
| Resource OCC | TBD | TBD | TBD | TBD | TBD |
| AgentTxn | TBD | TBD | TBD | TBD | TBD |

## Table B — Ablations

| Variant | Violation Rate | False Blocks | Throughput |
|---|---:|---:|---:|
| Full AgentTxn | TBD | TBD | TBD |
| No semantic invariants | TBD | TBD | TBD |
| UNKNOWN→FAILED | TBD | TBD | TBD |
| UNKNOWN→CONFIRMED | TBD | TBD | TBD |
| No reconciliation | TBD | TBD | TBD |
| LLM-only judge | TBD | TBD | TBD |

Never populate results before experiments.

---

# 46. Milestones

## M0 — Feasibility spike

- repository skeleton,
- two mock services,
- effect ledger,
- one invariant,
- deterministic fault injection,
- two concurrent scripted agents,
- naive + resource OCC + AgentTxn comparison.

**Exit condition:** demonstrate one real semantic conflict that resource-only logic misses.

---

## M1 — Effect model

- certainty-state machine,
- tool contracts,
- reconciliation,
- idempotency handling,
- structured event log.

---

## M2 — Runtime

- commit certifier,
- dependency tracking,
- waiting/wakeup logic,
- compensation path,
- invariant registry.

---

## M3 — TxnAgentBench Commerce

- scenario schema,
- commerce services,
- fault schedule,
- baseline runner,
- evaluator.

---

## M4 — Concurrency study

- workload generator,
- semantic-conflict scenarios,
- concurrency scaling,
- resource OCC baseline,
- serial baseline.

---

## M5 — Second domain

- Identity/SaaS,
- cross-service invariants,
- domain-independent runtime verification.

---

## M6 — LLM integration

- one tool-calling agent,
- one provider/model,
- controlled seeds,
- agent-runtime interaction analysis.

---

## M7 — Ablations and final protocol

- frozen scenarios,
- frozen metrics,
- hypothesis tests,
- repeated runs.

---

## M8 — Final artifact

- README,
- architecture diagram,
- benchmark documentation,
- reproducible scripts,
- plots/tables,
- short demo video,
- technical report.

---

# 47. Suggested five-week schedule

## Week 1
Feasibility spike only.

Goal:
prove the central semantic-conflict thesis.

Do not build the full architecture if this fails.

## Week 2
Core effect ledger, certainty semantics, tool contracts, reconciliation, Commerce benchmark.

## Week 3
Commit certifier, concurrency logic, baselines, fault matrix.

## Week 4
Second domain, LLM integration, capability ablations.

## Week 5
Final experiments, repeated runs, statistical analysis, README/report/demo.

If the academic schedule is tighter, the third domain is the first thing to cut.

---

# 48. Week-1 backlog

1. Create repo.
2. Add `pyproject.toml`.
3. Configure Ruff, typing, pytest.
4. Add CI.
5. Create Payment service.
6. Create Shipping service.
7. Create PostgreSQL effect ledger.
8. Define `EffectIntent`.
9. Define certainty enum.
10. Implement fault injector.
11. Add `timeout_after_effect`.
12. Implement naive baseline.
13. Implement simple resource OCC baseline.
14. Implement `shipment_requires_confirmed_payment`.
15. Add two concurrent scripted agents.
16. Demonstrate timeout-after-charge + concurrent shipment.
17. Add true disjoint-resource semantic conflict.
18. Confirm resource OCC misses it.
19. Confirm AgentTxn catches it.
20. Write results into `experiments/week1.md`.
21. Decide GO / REDESIGN / STOP.

---

# 49. Week-1 deliverable

A single reproducible command:

```bash
python -m experiments.week1_semantic_conflict \
  --seed 42 \
  --baseline all
```

Output:

```text
Scenario 1: ambiguous payment + shipment
Scenario 2: disjoint-resource semantic conflict

naive:
  violations = ...

resource_occ:
  violations = ...

agenttxn:
  violations = ...
```

Plus a trace file for each run.

---

# 50. Definition of done

AgentTxn is done when:

- [ ] central semantic-conflict failure is demonstrated,
- [ ] semantic invariants span non-overlapping resources,
- [ ] `UNKNOWN` is first-class and experimentally justified,
- [ ] effect certainty transitions are tested,
- [ ] tool capabilities are explicit,
- [ ] naive baseline exists,
- [ ] serial baseline exists,
- [ ] idempotency baseline exists,
- [ ] Saga baseline exists,
- [ ] resource OCC baseline exists,
- [ ] at least one stronger research-inspired baseline exists if feasible,
- [ ] concurrency benchmark exists,
- [ ] deterministic fault injection exists,
- [ ] at least two realistic domains exist,
- [ ] LLM agent integration exists,
- [ ] primary ablations are complete,
- [ ] correctness and useful parallelism are both measured,
- [ ] CI passes,
- [ ] Docker Compose reproduction works,
- [ ] final metrics are derived from frozen experiments,
- [ ] no result is fabricated or estimated,
- [ ] novelty was re-checked before public release.

---

# 51. Novelty kill criteria

Stop or redesign if a new paper/system is found that already provides nearly all of:

1. concurrent LLM agents,
2. heterogeneous side-effecting services,
3. semantic invariants across non-overlapping resources,
4. explicit `UNKNOWN` state,
5. online commit decisions,
6. dynamic agent activity,
7. realistic delayed/ambiguous external faults,
8. concurrency benchmark,
9. correctness-vs-parallelism evaluation.

Also stop if Week 1 shows that the “semantic conflict” examples can be reduced to ordinary resource locking without loss of generality.

---

# 52. Risk register

## R1 — Project becomes database engineering with an LLM label

Mitigation:
- benchmark real agent workflows,
- include stochastic tool-using agents only after runtime core is correct,
- study how long LLM reasoning interacts with transactional state.

## R2 — Runtime serializes everything

Mitigation:
- make throughput/useful parallelism a primary metric,
- independent operations must proceed concurrently.

## R3 — Invariants are hand-written, so project seems trivial

Mitigation:
- the research question is not writing the rules,
- it is **online enforcement across concurrent heterogeneous effects with uncertainty**,
- show failures resource-level protocols cannot detect.

## R4 — Impossible cross-service guarantees

Mitigation:
- publish capability-dependent guarantees,
- explicitly model `UNKNOWN`,
- never claim universal atomicity.

## R5 — Baselines are strawmen

Mitigation:
- implement realistic idempotency, Saga, and OCC baselines,
- add a stronger paper-inspired baseline if feasible,
- document fidelity limits.

## R6 — Benchmark is too artificial

Mitigation:
- model known production semantics:
  - idempotency keys,
  - delayed consistency,
  - asynchronous commit,
  - approval workflows,
  - inventory reservation,
  - irreversible messaging.

## R7 — LLM randomness overwhelms systems result

Mitigation:
- establish the property with deterministic scripted agents first,
- then use LLMs as a stressor.

---

# 53. What would make this project exceptional

AgentTxn is not exceptional because it uses multiple agents.

It is not exceptional because it uses PostgreSQL, FastAPI, LangGraph, or Docker.

It becomes exceptional if the final result shows:

> **Two individually valid agent actions can violate a real cross-service invariant even though ordinary resource-level concurrency control sees no conflict, and AgentTxn prevents those failures while preserving significantly more concurrency than serial execution, including when external action outcomes are uncertain.**

That is the result to chase.

---

# 54. Interview explanation

A strong eventual explanation:

> “I studied a failure mode in tool-using AI agents that most frameworks treat poorly: several agents can concurrently make real API calls that are individually valid but jointly inconsistent, and a timeout does not always tell you whether the external action happened. I built AgentTxn, a runtime that tracks external effects as confirmed, failed, or unknown and evaluates cross-service business invariants before consequential actions commit. I also built a fault-injection benchmark with stale reads, delayed commits, retries, and irreversible effects, then compared the runtime against serial execution, idempotency, Saga recovery, and resource-level concurrency control.”

---

# 55. Future resume bullet template

Do **not** use until results exist.

Potential structure:

> Built **AgentTxn**, a semantic-concurrency runtime and benchmark for tool-using LLM agents across heterogeneous APIs; reduced cross-service invariant violations by **X%** versus resource-level concurrency baselines while preserving **Y%** more throughput than serial execution under stale reads, retries, and ambiguous external effects.

Second possible bullet:

> Designed deterministic fault injection for delayed commits, lost acknowledgements, duplicate delivery, compensation failures, and concurrent semantic conflicts across **N** workflows / **M** services; evaluated correctness, p95 certification overhead, recovery, and useful parallelism across **K** baselines.

---

# 56. Public README positioning

Do not headline it as:

> “ACID for AI agents.”

Do not headline it as:

> “Transactions for LangGraph.”

Preferred:

> **AgentTxn is an experimental runtime and benchmark for semantic concurrency in tool-using AI agents. It studies cases where concurrent actions touch different services or records but jointly violate a business invariant, especially when external effects may be delayed or ambiguous after timeouts.**

Then immediately show one concrete failure trace.

---

# 57. Demo requirement

The final demo should be understandable in under 30 seconds.

Example:

```text
Agent A: charge customer
Payment API: timeout
Reality: charge succeeded
Runtime state: UNKNOWN

Agent B: ship order
Naive runtime: ships
AgentTxn: blocks and reconciles payment

Provider confirms charge
AgentTxn: releases shipment
```

Then show a second case where two operations touch different resources but violate one shared business invariant.

The second case is essential because the first alone can be dismissed as retry/idempotency engineering.

---

# 58. Required technical report sections

Final report:

1. Problem
2. Failure model
3. Related work
4. Threat / execution model
5. Semantic Effect Graph
6. Effect certainty semantics
7. Commit certification protocol
8. Benchmark design
9. Baselines
10. Experimental protocol
11. Main results
12. Ablations
13. Performance overhead
14. Failure analysis
15. Guarantee boundaries
16. Threats to validity
17. Limitations
18. Future work

---

# 59. Guarantee statement

The README/report must include an explicit bounded guarantee such as:

> AgentTxn does not provide universal atomicity across arbitrary external services. Its guarantees are conditional on declared tool capabilities and executable application invariants. When an external effect cannot be safely reconciled or compensated, the runtime preserves uncertainty and blocks dependent consequential actions rather than guessing an outcome.

This is a strength, not a weakness.

---

# 60. First meaningful milestone

Before building agents, dashboards, adapters, or deployment infrastructure, prove this:

> **A pair of concurrent actions that do not share a raw resource conflict can still violate a meaningful cross-service invariant, a resource-level baseline misses the conflict, and AgentTxn detects it before both effects commit.**

If that is not demonstrated convincingly, stop and redesign the project.

That is the first real test of whether AgentTxn deserves to become the flagship.
