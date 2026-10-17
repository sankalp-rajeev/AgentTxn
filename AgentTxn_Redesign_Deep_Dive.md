# AgentTxn Redesign Deep Dive
## Unresolved external effects, downstream admission, and whether a defensible research gap remains

**Date:** 16 October 2026  
**Search cutoff:** 16 October 2026  
**Project:** AgentTxn  
**Trigger:** Week-one Gate 1 returned **REDESIGN** because a synthetic shared budget key allowed ordinary OCC to prevent the same compensation-budget race that AgentTxn prevented.

# 1. Executive verdict

## Verdict: **YELLOW — one tightly scoped Gate 1B is justified; the full redesign is not yet green.**

The proposed pivot:

> “Propagate an UNKNOWN external effect into downstream workflows and admit only the actions that remain safe.”

is **not sufficiently novel by itself**.

A deeper search found several pieces of prior work that occupy substantial parts of this idea:

- **TCT / Cognitive Serializability (2026 preprint)** already represents **Outcome Unknown**, uses receipt-driven reconciliation, captures a complete dependency vector, and provides **Effect-Compatible Cognitive Admission** using a joint predicate over current dependencies.
- **Atomix (2026 preprint)** already prevents a stalled/conflicting resource scope from delaying unrelated scopes; this is a direct prior-art analogue to “block only the affected work.”
- **Cognitive Admission Control (CAC, 2026 preprint)** already models unresolved obligations explicitly and converts them into defer/evidence-acquisition decisions.
- **Assurance-Aware Semantic Scheduling (AAS, 2026 preprint)** already schedules evidence acquisition and performs receipt-aware repair after timeout.
- **LIMBO / Where Does Exactly-Once Live? (2026 preprint)** already studies ambiguous side-effect outcomes, late commits, read-back, redelivery, idempotency, and the limits of verification-only recovery.
- **Cordon (2026 preprint)** already builds a semantic dependency graph across tool results and side effects.
- Classical distributed-systems/database work is also directly relevant:
  - **Escrow transactions (ACM TODS 1986)** already localize blocking while preserving safe concurrent work.
  - **Sagas (SIGMOD 1987)** and later semantic-isolation countermeasures make pending/uncertain business state visible to concurrent work.
  - **Semantic ACID (Software: Practice and Experience 1998)** explicitly uses semantic countermeasures to regain selected isolation across independent systems.
  - **Invariant Confluence (PVLDB 2015)** formalizes when application invariants actually require coordination rather than globally serializing work.
  - **Transaction Chopping (ACM TODS 1995)** is another classical example of extracting more concurrency while preserving a correctness condition.

Therefore:

> **“UNKNOWN propagation” and “minimal blocking” cannot be the novelty claim.**

However, a narrower empirical/systems question still appears defensible enough to test:

> **Given identical dependency metadata and identical tool capabilities, can we contain the blast radius of an unresolved external effect more precisely than transaction-level or resource-scope baselines, without permitting unsafe commits?**

The candidate mechanism is best described as **conditional uncertainty containment** or **effect-outcome slicing**, not generic uncertainty-aware admission.

The scientific contribution would need to be one or both of:

1. **A benchmark/failure model** that measures how one ambiguous external effect propagates into multiple concurrent workflows and quantifies *collateral blocking* as a first-class metric.
2. **A runtime mechanism** that evaluates downstream actions against the *set of still-possible external worlds*, admitting an action only if it is safe under every outcome consistent with the current evidence, while avoiding conservative blocking of actions whose safety is outcome-independent.

Even this is not automatically novel. If a TCT-like recertifier or an Atomix-style scope scheme, given equivalent metadata, matches the mechanism, **AgentTxn should be retired as the flagship rather than repeatedly narrowed**.

That is what Gate 1B must determine.

# 2. Why Week 1 changed the research question

Week one proved something useful but also falsified the strongest original thesis.

The compensation-budget scenario initially looked like a semantic conflict:

```text
Agent A:
refund $300

Agent B:
grant $300 account credit

Business invariant:
total incident compensation <= $500
```

Bare resource OCC misses the conflict because the two actions touch different physical resources.

But once OCC is given:

```text
semantic coordination key = incident_budget:{incident_id}
```

ordinary OCC can serialize the same logical contention.

That means the prior claim:

> “semantic conflicts fundamentally escape resource coordination”

is too strong.

A semantic invariant can often be converted into a synthetic coordination resource, predicate lock, escrow counter, versioned aggregate, or application-level semantic lock.

The important methodological lesson is:

> A baseline is not fair if AgentTxn receives semantic information that the baseline is not allowed to encode.

Every redesigned experiment must therefore use **matched information**.

# 3. Exact claim under audit

The revised idea proposed after Week 1 was:

> An external effect A becomes genuinely UNKNOWN. Several other agents are concurrently trying to act. Instead of globally halting, the runtime should identify which downstream actions truly depend on A and allow everything else to proceed.

Illustration:

```text
Agent A:
charge(order=123)
        |
        | response lost
        v
payment effect = UNKNOWN

Agent B:
ship(order=123)

Agent C:
issue replacement charge(order=123)

Agent D:
update unrelated customer profile

Agent E:
reserve downstream inventory
```

Desired behavior:

```text
B -> WAIT / RECONCILE
C -> WAIT or bind to same logical operation identity
D -> COMMIT
E -> depends on actual invariant
```

The question is whether this is actually a new systems contribution rather than a rephrasing of semantic locking, dependency tracking, resource-scoped frontiers, conditional admission, recertification, speculative execution, or classical coordination avoidance.

# 4. Search methodology

This audit deliberately expanded beyond “LLM agent transaction” queries.

Agent-specific search families included combinations of:

```text
LLM agent unknown outcome
ambiguous external effect agent
in-doubt tool call
receipt reconciliation agent
downstream effect dependency agent
multi-agent concurrency tool calls
semantic admission agent
effect-compatible admission
uncertainty-aware admission
semantic scheduling agents
resource-local blocking agent runtime
agent side-effect partial failure
exactly-once LLM agent
tool contract idempotency
speculative action tool agent
```

Classical systems search families included:

```text
in-doubt distributed transaction
escrow transaction long lived
semantic lock multidatabase
semantic ACID
transaction chopping
invariant confluence
coordination avoidance
saga isolation
compensating transaction
long-lived transaction concurrency
minimal blocking transaction
conditional dependency transaction
```

This report separates peer-reviewed prior art from 2026 frontier preprints. ArXiv publication is not treated as peer review.

# 5. The strongest direct novelty threat: TCT

**Jun He, Deying Yu. _When AI Agents Commit: Cognitive Serializability Across Data, Evidence, Policy, and Authority._ arXiv:2609.20261, 2026. Preprint.**

Source: https://arxiv.org/abs/2609.20261

TCT is much closer to the redesigned AgentTxn than the earlier survey initially recognized.

Its weaker correctness profile, **Effect-Compatible Cognitive Admission (TCT-C)**, does not require preserving the agent's original stochastic reasoning history. Instead, the effect can commit only after recertification against a current dependency vector, current policy, and a joint cross-dependency predicate.

TCT explicitly says independent approvals of individual dependencies are insufficient when a **joint predicate** matters. This is structurally similar to the Week-1 budget lesson: values may each appear individually compatible while their combination violates an aggregate predicate.

TCT also already has:

```text
Tentative
-> Committed Pending
-> Aborted
-> Outcome Unknown
```

`Outcome Unknown` is explicitly the client/epistemic state after a lost response. The client retries or queries by stable ID until it observes a durable receipt or otherwise resolves the competitor outcome.

So these cannot be AgentTxn novelty claims:

```text
first UNKNOWN state for agents
first receipt-driven reconciliation
first current-state recertification
first cross-dependency invariant at admission
```

TCT also states an observational-equivalence boundary: if two real histories look identical to a gate but a proposed action is valid in one and invalid in the other, no protocol can simultaneously guarantee zero-error soundness and positive progress for that indistinguishable pair.

This matters directly. AgentTxn cannot promise to “solve uncertainty” when the tool boundary does not expose enough evidence.

The possible surviving wedge is narrower: TCT is framed around admitting a concrete proposed effect at a commit boundary. Its evaluation is not obviously centered on:

```text
one unresolved external effect
-> many concurrently arriving downstream workflows
-> quantify exactly which actions are blocked
-> quantify unnecessary collateral blocking
-> optimize safe progress across that fan-out
```

That difference is real enough to test, but not enough to claim novelty without experiment.

# 6. Cognitive Admission Control (CAC)

**Jun He, Deying Yu. _Cognitive Admission Control: Risk-Conditioned Assurance for Consequential Actions in Agentic Distributed Systems._ arXiv:2609.16313, 2026. Preprint.**

Source: https://arxiv.org/abs/2609.16313

CAC turns an action into assurance obligations constraining predicates, evidence classes, scope, freshness, and witness-set requirements.

Its evaluator returns:

```text
satisfied
violated
unresolved
```

Operational decisions include:

```text
Permit
Deny
Defer
Escalate
Abort
```

Unresolved obligations create targeted evidence-acquisition requests.

Therefore:

> “If something is unresolved, defer and acquire missing evidence rather than force binary allow/deny”

is already covered.

The remaining difference is that CAC primarily reasons about assurance for **one consequential action**, while the redesigned AgentTxn would study how one unresolved external effect constrains a **set of concurrent dependent and independent actions**.

# 7. Assurance-Aware Semantic Scheduling (AAS)

**Jun He, Deying Yu. _Before Agents Act: Assurance-Aware Semantic Scheduling for Evidence Acquisition in Distributed Systems._ arXiv:2609.34376, 2026. Preprint.**

Source: https://arxiv.org/abs/2609.34376

AAS treats evidence gathering as scheduling under freshness, quorum, diversity, deadlines, and resource constraints. It also contains receipt-aware repair after selected operations time out.

This removes another easy claim:

> “Reuse evidence, gather only what is missing, and repair the schedule after timeout.”

The difference is that AAS schedules **evidence acquisition**. Our candidate uncertainty is stronger: the consequential external action itself may have happened, and other workflows are trying to perform new side effects while that fact remains unresolved.

# 8. Atomix: the strongest minimal-blocking threat

**Bardia Mohammadi et al. _Atomix: Timely, Transactional Tool Use for Reliable Agentic Workflows._ arXiv:2602.14849, 2026. Preprint.**

Source: https://arxiv.org/abs/2602.14849

Atomix uses per-resource progress frontiers. Its key property for this redesign is that **a stalled scope does not delay unrelated work**.

It also classifies effects by reversibility and surfaces unresolved residue.

This creates a major threat: if every AgentTxn semantic dependency can simply be encoded as an Atomix scope, then AgentTxn's selective blocking reduces to better metadata supplied to an existing resource-frontier idea.

The candidate distinction is therefore not “affected scope.” It would have to be **outcome-conditioned dependency**.

For example:

```text
if U committed:
    dependency set = {B, C}

if U did not commit:
    dependency set = {C, E}

if U is still possibly in-flight:
    dependency set = {B, C, F}
```

A conservative union scope is `{B, C, E, F}`. A conditional model might admit actions safe under every still-possible branch without waiting for U to resolve.

But Gate 1B must demonstrate that a strong scope scheme cannot encode the same precision without essentially becoming the same algorithm.

# 9. LIMBO / exactly-once work

**Jiapeng Li. _Where Does Exactly-Once Live? Model, Harness, and Tool-Contract Effects on Duplicate Side Effects in LLM Agents._ arXiv:2609.29095, 2026. Preprint.**

Source: https://arxiv.org/abs/2609.29095

LIMBO studies six services and twelve boundary fault modes, including late commits, redelivery, partial batches, eventual consistency, and optional idempotency.

Its key result is that when immediate read-back can reveal what happened, reasoning/reconciliation may recover; when a request remains in flight or was delivered twice, tool-contract support such as idempotency dominates.

It also proves that verification-only recovery cannot guarantee exactly-once behavior under unbounded late commits without stronger contract support.

AgentTxn therefore cannot claim discovery of ambiguous outcomes, the need for reconciliation, or the need for idempotency/tool contracts.

The possible surviving question starts after LIMBO's core question:

```text
write A is still unresolved
other workflows B...N arrive
what may safely proceed?
```

# 10. Agent–tool effect anomaly model

**Artem Trofimov, Boris Novikov. _When Tool Calls Succeed but Workflows Fail: Anomalies at the Agent-Tool Boundary._ arXiv:2609.15397, 2026. Preprint.**

Source: https://arxiv.org/abs/2609.15397

This work separates what happened externally from what the runtime observed and catalogs eight anomaly types under retries, speculation, concurrency, and partial failure.

It explicitly includes cases where committed effects depend on provisional state later withdrawn and derives the tool-boundary capabilities required to exclude anomaly classes.

AgentTxn should reuse this as a fault-model foundation. It cannot claim observation/effect separation as new.

# 11. Cordon

**Zheng Chen et al. _Cordon: Semantic Transactions for Tool-Using LLM Agents._ arXiv:2606.17573, 2026. Preprint.**

Source: https://arxiv.org/abs/2606.17573

Cordon already builds semantic lineage across tool results and later side effects. Its dependency relation covers earlier events influencing arguments, payloads, decisions, mutations, validation outcomes, or sinks.

So “track semantic dependencies between tool results and later side effects” is not enough.

Cordon is mostly task-scoped. Gate 1B would focus specifically on uncertainty crossing workflow boundaries and selectively constraining other concurrent transactions.

# 12. Classical prior art is not optional

The redesigned question is fundamentally connected to transaction processing, so older work matters.

## Escrow transactions — ACM TODS 1986

Patrick E. O'Neil, **The Escrow Transactional Method**, ACM TODS 11(4), 1986, DOI 10.1145/7239.7265.

Escrow allows long-lived transactions to update invariant-constrained quantities without blocking every concurrent operation. It embodies the principle “quarantine only what is actually at risk.”

If a proposed AgentTxn scenario reduces to budget, inventory, quota, or capacity reservation, escrow may already be the cleanest solution.

## Sagas — SIGMOD 1987

Hector Garcia-Molina and Kenneth Salem, **Sagas**, SIGMOD 1987.

Sagas split long-lived transactions into interleavable subtransactions with compensation. Later semantic-lock practices explicitly make pending business state visible so concurrent workflows can wait, reject, or proceed carefully.

## Transaction Chopping — ACM TODS 1995

Shasha et al., **Transaction Chopping: Algorithms and Performance Studies**, ACM TODS 20(3), 1995.

Again the systems objective is familiar: increase concurrency without violating the required correctness condition.

## Semantic ACID — Software: Practice and Experience 1998

Lars Frank and Torben U. Zahle, **Semantic ACID Properties in Multidatabases Using Remote Procedure Calls and Update Propagations**, 1998.

This paper explicitly uses semantic consistency and isolation countermeasures across systems without one shared transaction manager.

## Invariant Confluence — PVLDB 2015

Peter Bailis et al., **Coordination Avoidance in Database Systems**, PVLDB 8(3), 2015.

Invariant confluence formalizes when application invariants require coordination. It is direct conceptual prior art for “coordinate only where the invariant actually requires it.”

Therefore AgentTxn should not claim a new general theory of minimal coordination.

# 13. Speculative downstream execution

Two additional neighbors matter.

**Speculative Actions** predicts and prelaunches downstream agent actions while an authoritative actor catches up. Its safety envelope restricts risky speculation to idempotent, reversible, or sandboxed effects.

Microsoft Research's **Sherlock** speculatively executes downstream workflow nodes while verification runs and rolls back if verification fails.

So “keep useful downstream work moving while upstream certainty is pending” also has prior art.

The redesigned case must remain specifically about **real external effects whose upstream real-world outcome may already be committed but unobservable**, not just reversible speculative computation.

# 14. What is definitely not novel

Do not pitch AgentTxn as:

```text
first UNKNOWN state for agents
first uncertainty-aware admission
first minimal-blocking agent runtime
first semantic dependency graph
first concurrent agent transaction system
first way to continue unrelated work while one operation stalls
first exactly-once/retry-safe agent runtime
first semantic isolation for heterogeneous services
first invariant-based concurrency mechanism
first speculative downstream agent execution
```

# 15. What may still be open enough to test

The narrow candidate is **Effect Uncertainty Containment**.

Let:

```text
U = unresolved effects
W(U) = external worlds consistent with current receipts,
       time bounds, tool contracts, and observations
a = candidate downstream action
I = application invariants
R = recoverability requirements
```

Define:

```text
SafeNow(a, U) =
    for every w in W(U):
        I(execute(a, w)) holds
        and R(execute(a, w)) holds
```

Then:

```text
if SafeNow(a, U):
    admit a
elif a is unsafe in every world:
    block
else:
    wait for distinguishing evidence / reconcile / escalate
```

This is conservative by design.

If the candidate is safe in one possible world and unsafe in another, and the runtime cannot distinguish those worlds, TCT's observational-equivalence result says a zero-error runtime cannot both safely commit and guarantee progress.

The possible benefit is therefore **less collateral blocking at equal safety**.

# 16. Why this may still collapse

A strong baseline can create a synthetic scope from the uncertainty dependency set and coordinate on it.

A strong TCT-C-like baseline can treat UNKNOWN as part of the complete dependency vector and run the same joint predicate.

If either can make the same decisions with the same metadata, the new mechanism is repackaging.

This is why the next experiment must be an equivalence test, not a feature build.

# 17. The strongest possible surviving distinction

The most plausible wedge is **conditional rather than unconditional dependency**.

Static scope systems usually encode:

```text
A may affect B
```

and therefore coordinate conservatively.

But one unresolved external effect has outcome-dependent structure:

```text
if U = committed:
    dependency set = {B, C}

if U = absent:
    dependency set = {C, E}

if U = still possibly in-flight:
    dependency set = {B, C, F}
```

The union is safe but may overblock.

An outcome-conditioned runtime could admit an action if it is safe in **every** possible branch, even before the branch resolves.

This is a legitimate systems idea, but it is conceptually related to contingent planning, invariant-based coordination, and semantic concurrency control. The safe research claim is not “we invented this general principle.” The safe claim would be a new **agent-tool benchmark and runtime treatment** of conditional external-effect uncertainty.

# 18. Benchmark redesign: TxnAgentBench-U

The benchmark should measure **uncertainty fan-out across concurrent workflows**.

Each scenario contains:

```text
1 unresolved upstream external effect
N concurrent candidate downstream effects
a known set of possible external resolutions
dependency/invariant metadata
matched tool capabilities
a deterministic fault schedule
an oracle for which actions are safe before resolution
```

New primary metrics:

```text
unsafe_commit_rate
invariant_violation_rate
duplicate_effect_rate
irrecoverable_residue_rate

safe_actions_admitted_before_resolution
safe_actions_unnecessarily_blocked
collateral_block_rate
mean blocked action fan-out
uncertainty blast radius

throughput
completion latency
time waiting on irrelevant uncertainty
```

The key plot is:

```text
unsafe commits
vs
collateral blocking
```

# 19. Matched-information baselines

Every baseline receives the same:

```text
tool contracts
logical operation IDs
reconciliation endpoints
idempotency support
compensation metadata
dependency declarations
application invariants
fault schedule
external observations
```

Only the decision policy may differ.

**B0 — Global fail-closed:** any relevant UNKNOWN blocks all downstream effects.

**B1 — Synthetic-scope OCC:** encode complete semantic scopes. This is the baseline that killed the Week-1 claim.

**B2 — Atomix-inspired frontier:** dependency/resource scopes have local frontiers; unrelated scopes progress.

**B3 — Semantic-lock/pending-state baseline:** unresolved business effects are marked pending and consumers respect that status.

**B4 — TCT-C-inspired joint recertification:** each candidate evaluates a complete current dependency vector and joint predicate.

**B5 — Outcome-Conditioned Admission (OCA):** evaluate safety across every still-possible outcome world.

If B4 and B5 are effectively equivalent in realistic cases, the runtime redesign is dead.

# 20. Gate 1B experiment

Do not implement the full old Week 2.

Build one surgical experiment.

Create one unresolved effect with possible states:

```text
COMMITTED
ABSENT
STILL_IN_FLIGHT
```

Then submit 6–10 concurrent candidate actions divided into:

```text
Class A: unsafe in every world
Class B: safe in every world
Class C: safe only if COMMITTED
Class D: safe only if ABSENT
Class E: safe if COMMITTED or ABSENT,
         unsafe while a late commit is still possible
```

All baselines receive the same metadata.

At least one Class-B action should share enough coarse context with the unresolved effect that a broad fail-closed or union-scope policy blocks it, while the outcome-conditioned evaluator proves it safe.

But the TCT-C-inspired baseline must also be allowed to prove it safe. Do not weaken it.

# 21. Candidate scenario

Commerce:

```text
U = payment capture for order O
```

After timeout:

```text
W1 = capture committed
W2 = capture definitely absent
W3 = capture still in flight
```

Concurrent candidates:

```text
A: ship order O
B: create internal support note for O
C: send "payment confirmed" email
D: update customer marketing preference
E: reserve packaging material for O
F: retry using same logical operation ID
G: initiate a different payment method
H: cancel order
```

Some are safe in all worlds; others are outcome-sensitive.

A second scenario should cross workflow boundaries, for example an UNKNOWN refund on Order A while separate agents attempt customer credit, replacement shipment, fraud hold, loyalty recalculation, and unrelated profile updates.

The second case is important because one broad `order:{id}` lock should not define the whole result.

# 22. Gate 1B success criteria

Proceed only if all are true:

**G1.** There are realistic actions safe in all possible worlds but blocked by meaningful coarse-grained baselines.

**G2.** OCA admits them with zero additional unsafe commits under exhaustive deterministic schedules.

**G3.** The improvement remains after every baseline receives the same semantic metadata and recovery capabilities.

**G4.** A TCT-C-inspired complete joint-recertification baseline does not trivially become identical to OCA.

**G5.** OCA cannot be reduced to simply adding a practical synthetic lock/scope per conditional dependency.

If **G4 or G5 fails, stop AgentTxn as a new runtime contribution.**

# 23. Expected death modes

**TCT-C equivalence:** if OCA is just the TCT-C joint predicate expressed as possible worlds, the mechanism is not differentiated.

**Scope equivalence:** if practical synthetic scopes reproduce the same decisions without overblocking, Atomix/OCC-style coordination is enough.

**Benchmark-only thinness:** if the only result is another timeout suite, LIMBO and the effect-anomaly work already occupy too much of that territory.

**Speculation equivalence:** if all admitted work is simply reversible/sandboxed speculation, Speculative Actions/Sherlock are strong substitutes.

# 24. Why the benchmark may still be independently useful

TxnAgentBench-U can measure a phenomenon current work does not foreground:

> **One unresolved real-world effect can impose a coordination tax on many other agent workflows.**

That tax has two sides:

```text
under-containment:
unsafe dependent actions proceed

over-containment:
safe outcome-insensitive actions stall
```

A benchmark that quantifies both could be useful even if the scheduler is simple.

# 25. Reuse the existing AgentTxn work

Do not rewrite the repository.

Keep:

```text
PostgreSQL effect ledger
six-state certainty model
logical operation identity
timeout-before/after-effect fault injection
provider/runtime trace separation
Docker reproduction
CI
scripted concurrency harness
payment/shipping/refund/credit services
replay/provenance machinery
```

Add only:

```text
possible outcome sets
conditional dependency predicates
candidate-action classifier
matched decision-policy interface
collateral-blocking metrics
TCT-C-inspired baseline
```

# 26. Why no LLM is needed for Gate 1B

The next question is a systems equivalence question:

```text
given identical metadata and unresolved-world information,
does one admission policy make strictly better decisions?
```

Use scripted concurrent clients.

LLM integration should return only if the systems claim survives.

# 27. Recommendation

## Do not start the original Week 2.

Run **Gate 1B only**, time-boxed to roughly 2–3 focused development days.

Deliverable:

```text
experiments/gate1b_uncertainty_containment.md
```

It should contain:

```text
exact claim
scenario definitions
possible-world oracle
matched metadata
global fail-closed baseline
synthetic-scope OCC
Atomix-inspired scope/frontier baseline
TCT-C-inspired joint recertifier
OCA
safety results
collateral-blocking results
equivalence analysis
GO / REDESIGN / STOP
```

# 28. Decision rule

**GREEN:** OCA provides a reproducible safety/progress point that strong matched baselines do not reproduce, and the difference is not metadata asymmetry.

**REDESIGN:** the uncertainty-fanout benchmark is interesting, but OCA is equivalent to TCT-C/scopes. Then AgentTxn may become a benchmark project rather than a novel transaction runtime.

**STOP:** both the mechanism and benchmark reduce cleanly to existing TCT/Atomix/LIMBO/classical patterns.

# 29. Current expectation

The probability that the **runtime mechanism itself** survives as clearly differentiated is moderate-to-low because TCT-C is broad, Atomix already localizes blocking, Cordon already tracks semantic dependency, and classical invariant/escrow work is powerful.

The probability that a **carefully controlled uncertainty-fanout benchmark plus an empirical finding about collateral blocking** survives is higher.

So the strongest possible final identity may be:

> **A benchmark-driven study of how ambiguous real-world effects propagate across concurrent AI-agent workflows, plus a reference uncertainty-containment scheduler.**

That is scientifically cleaner than forcing the original runtime claim.

# 30. Does it still meet the exceptional-project bar?

Only if the final result is strong.

A weak result:

```text
our scheduler blocks slightly less work
```

is not enough.

A strong result would conceptually look like:

```text
under identical tool and dependency metadata,
coarse fail-closed and scope-based policies either
(a) allow unsafe downstream effects, or
(b) unnecessarily stall a material fraction of outcome-insensitive work,

while outcome-conditioned admission preserves the same safety
and materially reduces collateral blocking across multiple fault classes/domains.
```

Do not invent numbers. The experiments must earn them.

# 31. Final conclusion

The deeper survey does **not** green-light “uncertainty-aware admission.”

It narrows the next defensible test to:

> **Under identical contracts, dependency metadata, and recovery capabilities, can outcome-conditioned admission reduce collateral blocking from unresolved external effects without increasing unsafe commits relative to strong scope/frontier and joint-recertification baselines?**

That is falsifiable and fair.

If Gate 1B shows TCT-C or an equally informed scope/frontier baseline matches AgentTxn, retire AgentTxn as the flagship.

If Gate 1B shows a reproducible gap under matched information, the project becomes substantially stronger because it has survived two adversarial design gates.

# 32. Core references

## Peer-reviewed / established systems

1. Patrick E. O'Neil. **The Escrow Transactional Method.** ACM TODS 11(4), 1986. DOI: 10.1145/7239.7265.
2. Hector Garcia-Molina, Kenneth Salem. **Sagas.** ACM SIGMOD, 1987. DOI: 10.1145/38713.38742.
3. Dennis Shasha et al. **Transaction Chopping: Algorithms and Performance Studies.** ACM TODS 20(3), 1995. DOI: 10.1145/211414.211427.
4. Lars Frank, Torben U. Zahle. **Semantic ACID Properties in Multidatabases Using Remote Procedure Calls and Update Propagations.** Software: Practice and Experience 28(1), 1998.
5. Peter Bailis et al. **Coordination Avoidance in Database Systems.** PVLDB 8(3), 2015.
6. Yuanbo Zhang et al. **DelAct: A Replayable Boundary Runtime for Auditable and Governed LLM Agent Workflows.** IEEE/ACM IWQoS 2026.

## Frontier agent-systems work

7. Jun He, Deying Yu. **When AI Agents Commit: Cognitive Serializability Across Data, Evidence, Policy, and Authority.** arXiv:2609.20261.
8. Jun He, Deying Yu. **Cognitive Admission Control: Risk-Conditioned Assurance for Consequential Actions in Agentic Distributed Systems.** arXiv:2609.16313.
9. Jun He, Deying Yu. **Before Agents Act: Assurance-Aware Semantic Scheduling for Evidence Acquisition in Distributed Systems.** arXiv:2609.34376.
10. Bardia Mohammadi et al. **Atomix: Timely, Transactional Tool Use for Reliable Agentic Workflows.** arXiv:2602.14849.
11. Jiapeng Li. **Where Does Exactly-Once Live? Model, Harness, and Tool-Contract Effects on Duplicate Side Effects in LLM Agents.** arXiv:2609.29095.
12. Artem Trofimov, Boris Novikov. **When Tool Calls Succeed but Workflows Fail: Anomalies at the Agent-Tool Boundary.** arXiv:2609.15397.
13. Zheng Chen et al. **Cordon: Semantic Transactions for Tool-Using LLM Agents.** arXiv:2606.17573.
14. Naimeng Ye et al. **Speculative Actions: A Lossless Framework for Faster Agentic Systems.** arXiv:2510.04371 / ICLR-2026-era work.
15. Yeonju Ro et al. **Sherlock: Reliable and Efficient Workflow Execution.** Microsoft Research, 2025.

---

# Bottom line

**Do not start Week 2. Run Gate 1B.**

The revised hypothesis is:

> **Under identical contracts, dependency metadata, and recovery capabilities, outcome-conditioned admission can reduce collateral blocking from unresolved external effects without increasing unsafe commits relative to strong scope/frontier and joint-recertification baselines.**

If that statement survives, AgentTxn is green again.

If it does not, retire AgentTxn as the flagship.
