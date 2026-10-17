# Gate 0: novelty check

Decision, 16 October 2026: proceed with the bounded feasibility experiment only.
The targeted search did not verify a single system demonstrating all nine PRD
capabilities. It did find substantial overlap and does not establish novelty.
Evidence and primary sources are recorded in [literature.md](literature.md).

The strongest risks are Atomix's semantic hook, SVBE's effect-time validation,
Limbo's ambiguous outcomes and capability-dependent recovery, and Authority at
Commit Time's semantic verification plus receipt reconciliation.

Before interpreting the disjoint-resource result, include an augmented resource
OCC control that declares incident:<id>:budget as a shared conflict key. A budget
counterexample can be encoded as an ordinary shared lock or synthetic resource.
If that control matches AgentTxn, the original stronger research claim does not
pass Gate 1; record REDESIGN rather than asserting novelty from a weak baseline.

The feasibility implementation is authorized to collect this evidence. Do not
advance to the full build or LLM integration unless the gate verdict supports it.
Full-text SVBE comparison and deeper adjacent-system review remain open research
tasks before a publication claim.

Gate 1 update: REDESIGN. The feasibility experiment confirms the synthetic
incident-budget key allows ordinary OCC to prevent the same budget race. The
stronger reduction check fails. See [week-one evidence](../experiments/week1.md).
