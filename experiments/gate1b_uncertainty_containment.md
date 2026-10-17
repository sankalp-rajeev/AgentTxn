# Gate 1B: uncertainty-containment feasibility

**Verdict: STOP for AgentTxn as a differentiated runtime contribution.**

This report is generated from the complete collected evidence, not estimated results.
The current research direction is AgentTxn_Redesign_Deep_Dive.md, which supersedes
conflicting parts of the old PRD. The original Week-2 build was not started.

## Exact hypothesis

Under identical metadata, invariants, contracts, idempotency, and reconciliation
capabilities, compensation metadata, fault schedules, and observations, OCA strictly
reduces collateral blocking versus strong scopes/frontiers and joint recertification
without increasing unsafe admission. Equivalence to either strong approach rejects
the runtime distinction; this gate does not claim novelty.

## Scenario definitions

Both scenarios have one genuinely UNKNOWN upstream effect and eight concurrent
scripted candidate workflows. Monetary values are integer cents. Candidate types
below are computed by the independent oracle; policies receive no safety labels.

### payment_fanout

- `unauthorized_export`: safe outcomes = none.
- `support_note`: safe outcomes = COMMITTED, ABSENT, IN_FLIGHT.
- `marketing_preference`: safe outcomes = COMMITTED, ABSENT, IN_FLIGHT.
- `reserve_packaging`: safe outcomes = COMMITTED, ABSENT, IN_FLIGHT.
- `ship_order`: safe outcomes = COMMITTED.
- `payment_confirmation`: safe outcomes = COMMITTED.
- `alternate_payment`: safe outcomes = ABSENT.
- `seal_payment_attempt`: safe outcomes = COMMITTED, ABSENT.

The complete scope compiler uses 10 distinct invariant/outcome slots.

### refund_cross_workflow

- `excess_credit`: safe outcomes = none.
- `incident_note`: safe outcomes = COMMITTED, ABSENT, IN_FLIGHT.
- `fraud_hold`: safe outcomes = COMMITTED, ABSENT, IN_FLIGHT.
- `profile_update`: safe outcomes = COMMITTED, ABSENT, IN_FLIGHT.
- `replacement_shipment`: safe outcomes = COMMITTED, ABSENT, IN_FLIGHT.
- `remove_refunded_loyalty`: safe outcomes = COMMITTED.
- `customer_credit`: safe outcomes = ABSENT.
- `seal_incident`: safe outcomes = COMMITTED, ABSENT.

The complete scope compiler uses 8 distinct invariant/outcome slots.

The payment case includes same-order support notes and packaging, an unrelated
marketing update, confirmed-payment shipment/email, an alternate payment, an
unauthorized export, and a billing-attempt seal. Sealing writes a terminal business
record and is prohibited while the original capture may still commit; it does not
undo a payment. The refund case crosses order/customer workflows: a 30000-cent
refund under a 50000-cent incident cap, a possible 30000-cent credit, an always
excessive 60000-cent credit, independently authorized replacement shipment, fraud
hold, profile/note changes, loyalty removal, and terminal incident sealing.

Realizations are hidden committed, hidden absent, in-flight then late commit,
and in-flight then terminal abort. Every realization starts with the same timeout
and opaque probes. Evidence rounds are full uncertainty, repeated full uncertainty,
authoritative quiescence retaining COMMITTED/ABSENT, and a terminal receipt.

## Possible-world oracle

The oracle constructs each concrete external world, applies candidate writes, and
evaluates every declared business invariant. IN_FLIGHT additionally explores both
terminal continuations. An absent receipt never rules out a late commit. A terminal
abort receipt is fenced against future writes with the same logical identity.

An action may COMMIT only if safe in every still-possible world and continuation;
BLOCK means unsafe in all current worlds; a mixed result requires WAIT. The oracle
is separate from the symbolic TCT/lock/scope implementation and OCA's interpreter.

The exhaustive audit covers all seven nonempty outcome sets: 112 candidate/outcome-set cases
per policy. It also checks 368 joint subsets of oracle-safe actions, including late continuations.

Candidate writes are distinct Boolean business facts and commute. The subset audit
checks joint invariant preservation; it is not a claim to enumerate all operating-
system schedules. All four declared provider fault schedules are executed.

## Matched metadata and execution

Every policy receives the identical immutable AdmissionView: complete candidate
intents and logical IDs, all semantic dependencies and invariant ASTs, complete
world bindings, per-action contracts, idempotency support, reconciliation endpoint,
compensation metadata, public fault schedule, and the same ordered observations.
Per-round SHA-256 input hashes are compared across all policies. Hidden provider
realization and future receipt values are evaluator-only; leaking them would erase
the uncertainty being studied. Each policy faces the same hidden realization within
a matched trial. Upstream probe results are broadcast at common logical rounds; no
policy receives a private successful probe. Compensation is declared unsupported
and is not used to excuse an unsafe effect.
Candidate Boolean flags encode the proposed-effect footprint, not hidden provider
observations. Actual prior effects are checked by the accumulated provider journal
and exhaustive joint-subset oracle. Mutable upstream state and stable permissions
form the shared dependency vector; admitted candidates commute in this workload.

The Week-1 coordinator, HTTP adapter, persistent ledger, identity checks, provider
journals, and Docker infrastructure execute admitted effects. WAIT returns to the
scripted evidence scheduler, then recertifies after the next shared observation.
The evidence round remains fixed through dispatch. Multiple independent admission
leaders and real-world unmediated writes remain outside this feasibility model.

## Baseline implementations

- Global fail-closed uses the complete invariant metadata but defers otherwise
  possible actions while the upstream outcome is unresolved; it is the deliberately
  coarse policy specified by the protocol, not a strong scope baseline.
- Synthetic-scope OCC compiles executable predicates into invariant/outcome conflict
  reservations and validates the current evidence revision before dispatch. Safe
  same-context actions do not acquire irrelevant payment/refund scopes.
- Atomix-inspired scope/frontier seals those complete scopes and checks local
  frontiers. Only incompatible still-possible outcomes hold a frontier back.
- Semantic pending-state/lock derives a full business-operation compatibility matrix
  over the same unresolved outcome modes.
- TCT-C-inspired joint recertification evaluates one symbolic predicate over the
  complete simultaneous current dependency vector, including temporal continuation.
- OCA constructs concrete possible worlds and directly interprets every invariant.

These are bounded admission models. They do not reproduce full Atomix or TCT
durability, authority, or distributed fencing protocols. TCT's joint recertifier
is intentionally permitted the same logical predicate as OCA; Atomix permits a
semantic pre-commit hook. See the primary sources:
[TCT section 4.4](https://arxiv.org/html/2609.20261#S4.SS4) and
[Atomix](https://arxiv.org/html/2602.14849). Equivalence here concerns these tested
decision models, not a theorem that the complete published systems are identical.

## Safety results

- `global_fail_closed`: unsafe admissions 0/256; unsafe actual commits 0/46; physical violation events 0; duplicate effects 0; irrecoverable violation residue 0.
- `synthetic_scope_occ`: unsafe admissions 0/256; unsafe actual commits 0/46; physical violation events 0; duplicate effects 0; irrecoverable violation residue 0.
- `atomix_scope_frontier`: unsafe admissions 0/256; unsafe actual commits 0/46; physical violation events 0; duplicate effects 0; irrecoverable violation residue 0.
- `semantic_pending_lock`: unsafe admissions 0/256; unsafe actual commits 0/46; physical violation events 0; duplicate effects 0; irrecoverable violation residue 0.
- `tct_c_joint_recertification`: unsafe admissions 0/256; unsafe actual commits 0/46; physical violation events 0; duplicate effects 0; irrecoverable violation residue 0.
- `agenttxn_oca`: unsafe admissions 0/256; unsafe actual commits 0/46; physical violation events 0; duplicate effects 0; irrecoverable violation residue 0.

Safety is checked both robustly against all possible worlds and against the actual
provider journal, including later completion of a previously in-flight effect.
No compensation recovery is claimed. Exact zero counts describe this finite workload,
not a population-level guarantee or empirical rate estimate for arbitrary services.

## Collateral-blocking results

The fixed denominator is all oracle-safe candidate/evidence-round opportunities
before the terminal receipt (rounds 0-2), including a decision panel for candidates
that already executed. This avoids comparing policy-dependent denominator sizes.
Distinct action counts are summed over the eight scenario/realization trials.

- `global_fail_closed`: collateral 92/92 (100.0%); distinct collateral actions 36; safe actions admitted before resolution 0; mean WAIT fan-out 7.000 actions per unresolved checkpoint.
- `synthetic_scope_occ`: collateral 0/92 (0.0%); distinct collateral actions 0; safe actions admitted before resolution 36; mean WAIT fan-out 3.167 actions per unresolved checkpoint.
- `atomix_scope_frontier`: collateral 0/92 (0.0%); distinct collateral actions 0; safe actions admitted before resolution 36; mean WAIT fan-out 3.167 actions per unresolved checkpoint.
- `semantic_pending_lock`: collateral 0/92 (0.0%); distinct collateral actions 0; safe actions admitted before resolution 36; mean WAIT fan-out 3.167 actions per unresolved checkpoint.
- `tct_c_joint_recertification`: collateral 0/92 (0.0%); distinct collateral actions 0; safe actions admitted before resolution 36; mean WAIT fan-out 3.167 actions per unresolved checkpoint.
- `agenttxn_oca`: collateral 0/92 (0.0%); distinct collateral actions 0; safe actions admitted before resolution 36; mean WAIT fan-out 3.167 actions per unresolved checkpoint.

Logical action-round waiting is recorded in the raw metrics. No wall-clock
throughput or latency advantage is inferred from these controlled rendezvous runs.

## Equivalence analysis

- `global_fail_closed` differs from OCA in 37/112 exhaustive candidate/outcome-set decisions (COMMIT, WAIT, and BLOCK).
- `synthetic_scope_occ` differs from OCA in 0/112 exhaustive candidate/outcome-set decisions (COMMIT, WAIT, and BLOCK).
- `atomix_scope_frontier` differs from OCA in 0/112 exhaustive candidate/outcome-set decisions (COMMIT, WAIT, and BLOCK).
- `semantic_pending_lock` differs from OCA in 0/112 exhaustive candidate/outcome-set decisions (COMMIT, WAIT, and BLOCK).
- `tct_c_joint_recertification` differs from OCA in 0/112 exhaustive candidate/outcome-set decisions (COMMIT, WAIT, and BLOCK).

TCT-C-inspired recertification and OCA differ in representation: symbolic
compatibility over the current vector versus explicit universal world simulation.
Both enforce the same supplied joint predicate. This equivalence is not an
improvement result for OCA and does not establish a new mechanism.

The practical scope compiler names each invariant/outcome incompatibility and
holds only still-possible conflict slots. It needs a bounded number of slots for
one effect with three outcomes and reproduces the same precision without measured
collateral blocking. It incorporates semantic predicates; the original paper is
not claimed to provide this compiler automatically. Removing that capability
would intentionally weaken an equally informed baseline and was not done.

The global barrier overblocks safe work, demonstrating the metric, but an OCA
advantage only over that barrier does not satisfy G4 or G5. The complete matched
joint-recertification and scope/frontier controls remove the apparent advantage.

## Verdict and limits

**STOP.** The differentiated runtime hypothesis does not survive the matched
equivalence test. Retain the harness as a regression/research artifact; do not
start the original Week-2 build or add LLM APIs on this evidence. This gate does
not independently validate novelty of a benchmark-only project.

The workload has two Commerce fan-outs, one unresolved effect, finite Boolean
predicates, immediate candidate effects, and a controlled authoritative evidence
schedule. The quiescence certificate is an explicit tool capability, not an
inference from waiting. Results do not establish equivalence for arbitrary
multi-effect or distributed workloads and must not be generalized beyond the model.

## Reproduction and provenance

```text
uv run --no-sync python -m experiments.gate1b_uncertainty_containment --seed 42 --baseline all
```

Use --ledger postgres with DATABASE_URL, or the Compose gate1b profile service.
Collected conditions: 48; seed 42; ledger memory.
Source commit: 6e4d95cd2abcd489e4971641f134d2431cfceda8.
Source-content SHA-256: 8df55f89fba0a2337110219ec00abe80957ec90fec191d07bb994d7de6a64ba5.
Dependency lock SHA-256: e64ecf3c1ed01d9418f68bc3af09489af3aaec4174bf61741f1add6e53fd9539.
Evidence directory used to generate this report: experiments/results/gate1b/memory.
Committed evidence is under experiments/results/gate1b/. The summary preserves
exact definitions, normalized input-document hashes, metadata hashes, provenance,
and metrics; each condition has separate runtime, provider, evidence, and decision
streams. In-memory replay is exact; PostgreSQL may reorder commuting completions.
Validation details and cross-mode comparison are recorded in experiments/protocol.md.

## Completed validation

- Full local suite: 45 passed with PostgreSQL and TCP integration enabled; no skips.
- Ruff and strict mypy passed.
- All implementation CI jobs passed on Python 3.11, Python 3.12, and Compose/PostgreSQL.
- All 48 conditions were reproduced in each of memory, host/PostgreSQL, and Docker/PostgreSQL.
- All 144 traces were independently replay-verified. Metric vectors, matched-input hashes,
  source-content hash, lockfile hash, and input-document hashes agree across modes.
- These execution modes are reproduction checks, not extra independent statistical repetitions.
- The deliberately unsafe test-only control creates detected unsafe commits and physical
  violations, proving the oracle/replay pipeline does not simply report zero for every policy.
- Development containers were used only for mock effects; no LLM or live payment API was called.

Implementation CI: https://github.com/sankalp-rajeev/AgentTxn/actions/runs/39002635113
