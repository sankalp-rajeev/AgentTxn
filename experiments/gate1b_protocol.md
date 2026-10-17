# Gate 1B protocol (declared before result collection)

The current direction is AgentTxn_Redesign_Deep_Dive.md. This is only the
uncertainty-containment feasibility gate; the old Week-2 build is excluded.

## Hypothesis and rejection rule

With identical semantic dependencies, invariants, contracts, capabilities,
faults, and observed evidence, OCA admits more actions safe in every still-
possible external world than strong scopes/frontiers and joint recertification,
with no additional unsafe admission.

Reject the runtime distinction if TCT-C-inspired joint recertification or a
practical synthetic-scope/frontier encoding reproduces OCA's decisions without
meaningful collateral blocking. No result or novelty claim is presupposed.

## Fixed finite workload

Two eight-candidate Commerce fan-outs: an uncertain payment capture and a refund
whose uncertainty crosses order/customer workflow boundaries. Both include
outcome-independent safe work, always-unsafe work, committed-only work, absent-
only work, and work unsafe while a late commit remains possible.

Four provider realizations per scenario: hidden committed, hidden absent,
in-flight then late commit, in-flight then terminal abort. All initially produce
the same timeout and unresolved probes. Each policy receives the same public
schedule and observation stream for that realization. Hidden provider truth is
reserved for evaluation, not included in the policy's dependency vector.

Logical evidence rounds: initial UNKNOWN with {COMMITTED, ABSENT, IN_FLIGHT};
a repeated unresolved probe; an authoritative no-in-flight certificate retaining
{COMMITTED, ABSENT}; then an authoritative terminal receipt. A missing receipt
alone never excludes IN_FLIGHT.

## Matched policies

Global fail-closed; synthetic-scope OCC; Atomix-inspired scope/frontier;
semantic pending-state/lock; TCT-C-inspired joint recertification; AgentTxn OCA.
Named research-inspired policies are bounded admission models, not full paper
reproductions. Strong scope/lock policies may compile the supplied semantic
predicates into compatibility scopes. TCT-C may use a complete joint predicate.

## Evaluation

Keep a full decision panel for every candidate and evidence round, even if an
action already executed, so collateral denominators are identical across
policies. Execute admitted effects once using the Week-1 coordinator, HTTP
adapter, mock provider journal, and memory/PostgreSQL ledger.

Primary safety: unsafe COMMIT count against all possible worlds, plus actual
provider-state violations including late completion. Primary progress:
oracle-safe candidates admitted before terminal resolution, collateral-blocked
safe opportunities and rate, and waiting fan-out. Report exact numerators and
denominators. Logical waiting rounds are deterministic; do not claim wall-clock
throughput improvements.

Exhaust all seven nonempty outcome sets for the classifier and equivalence
audit, and all four declared provider schedules. Check joint admitted subsets
and commuting candidate effects rather than claiming all operating-system
interleavings were enumerated.

Persist raw runtime/provider/decision/evidence traces, metadata hashes, source
commit and content hash, dependency lock hash, and input documents' hashes.
Preserve Week-1 behavior and tests. Verify the full suite, PostgreSQL, Docker,
and CI before completing Gate 1B. Produce gate1b_uncertainty_containment.md from
the collected evidence and state GO, REDESIGN, or STOP explicitly.

Pre-final validation clarifications: quiescence is explicitly declared in the
tool contract; repeated equal-valued observations still increment the evidence
revision. Candidate Boolean flags encode the proposed effect, while the joint
subset audit and provider journal check accumulated effects. These clarify the
representation and capabilities without changing the action classes, invariants,
fault branches, or the equivalence rejection rule.
