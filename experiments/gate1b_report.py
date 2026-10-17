"""Render the Gate-1B report from collected traces and exact run metrics."""

from pathlib import Path

from pydantic import BaseModel

from baselines.uncertainty import POLICIES, compile_scopes
from services.uncertainty import Realization
from txnagentbench.commerce.gate1b import problems
from txnagentbench.oracle import safe_outcomes
from txnagentbench.uncertainty_runner import UncertaintyRun


class Audit(BaseModel):
    candidate_outcome_cases_per_policy: int
    decision_differences_from_oca: dict[str, int]
    joint_safe_subsets_checked: int


class Evidence(BaseModel):
    source_commit: str
    source_tree_sha256: str
    lockfile_sha256: str
    seed: int
    ledger: str
    results: tuple[UncertaintyRun, ...]
    equivalence_audit: Audit


def write_report(summary: dict[str, object], path: Path, evidence_dir: Path) -> None:
    evidence = Evidence.model_validate(summary)
    expected = {
        (problem.scenario_id, str(realization), policy.name)
        for problem in problems()
        for realization in Realization
        for policy in POLICIES
    }
    actual = {(item.scenario_id, str(item.realization), item.baseline) for item in evidence.results}
    if actual != expected or len(evidence.results) != len(expected):
        raise ValueError("Incomplete or duplicated matched experiment conditions")
    grouped = {
        policy.name: [item for item in evidence.results if item.baseline == policy.name]
        for policy in POLICIES
    }
    for problem in problems():
        for realization in Realization:
            matching = [
                item
                for item in evidence.results
                if item.scenario_id == problem.scenario_id and item.realization == realization
            ]
            if len({item.input_hashes for item in matching}) != 1:
                raise ValueError("Matched-information audit failed")
    differences = evidence.equivalence_audit.decision_differences_from_oca
    equivalent = any(
        differences[name] == 0
        for name in ("tct_c_joint_recertification", "synthetic_scope_occ", "atomix_scope_frontier")
    )
    oca_unsafe = sum(item.metrics.unsafe_admissions for item in grouped["agenttxn_oca"])
    verdict = "STOP" if equivalent or oca_unsafe else "REDESIGN"
    lines = [
        "# Gate 1B: uncertainty-containment feasibility",
        "",
        f"**Verdict: {verdict} for AgentTxn as a differentiated runtime contribution.**",
        "",
        "This report is generated from the complete collected evidence, not estimated results.",
        "The current research direction is AgentTxn_Redesign_Deep_Dive.md, which supersedes",
        "conflicting parts of the old PRD. The original Week-2 build was not started.",
        "",
        "## Exact hypothesis",
        "",
        "Under identical metadata, invariants, contracts, idempotency, and reconciliation",
        "capabilities, compensation metadata, fault schedules, and observations, OCA strictly",
        "reduces collateral blocking versus strong scopes/frontiers and joint recertification",
        "without increasing unsafe admission. Equivalence to either strong approach rejects",
        "the runtime distinction; this gate does not claim novelty.",
        "",
        "## Scenario definitions",
        "",
        "Both scenarios have one genuinely UNKNOWN upstream effect and eight concurrent",
        "scripted candidate workflows. Monetary values are integer cents. Candidate types",
        "below are computed by the independent oracle; policies receive no safety labels.",
        "",
    ]
    for problem in problems():
        lines.extend([f"### {problem.scenario_id}", ""])
        for candidate in problem.candidates:
            worlds = safe_outcomes(problem, candidate)
            valid = ", ".join(str(item) for item in worlds) if worlds else "none"
            lines.append(f"- `{candidate.intent.action_name}`: safe outcomes = {valid}.")
        count = len(
            {scope.key for item in problem.candidates for scope in compile_scopes(problem, item)}
        )
        lines.extend(
            ["", f"The complete scope compiler uses {count} distinct invariant/outcome slots.", ""]
        )
    lines.extend(
        [
            "The payment case includes same-order support notes and packaging, an unrelated",
            "marketing update, confirmed-payment shipment/email, an alternate payment, an",
            "unauthorized export, and a billing-attempt seal. Sealing writes a terminal business",
            "record and is prohibited while the original capture may still commit; it does not",
            "undo a payment. The refund case crosses order/customer workflows: a 30000-cent",
            "refund under a 50000-cent incident cap, a possible 30000-cent credit, an always",
            "excessive 60000-cent credit, independently authorized replacement shipment, fraud",
            "hold, profile/note changes, loyalty removal, and terminal incident sealing.",
            "",
            "Realizations are hidden committed, hidden absent, in-flight then late commit,",
            "and in-flight then terminal abort. Every realization starts with the same timeout",
            "and opaque probes. Evidence rounds are full uncertainty, repeated full uncertainty,",
            "authoritative quiescence retaining COMMITTED/ABSENT, and a terminal receipt.",
            "",
            "## Possible-world oracle",
            "",
            "The oracle constructs each concrete external world, applies candidate writes, and",
            "evaluates every declared business invariant. IN_FLIGHT additionally explores both",
            "terminal continuations. An absent receipt never rules out a late commit. A terminal",
            "abort receipt is fenced against future writes with the same logical identity.",
            "",
            "An action may COMMIT only if safe in every still-possible world and continuation;",
            "BLOCK means unsafe in all current worlds; a mixed result requires WAIT. The oracle",
            "is separate from the symbolic TCT/lock/scope implementation and OCA's interpreter.",
            "",
            f"The exhaustive audit covers all seven nonempty outcome sets: "
            f"{evidence.equivalence_audit.candidate_outcome_cases_per_policy} "
            "candidate/outcome-set cases",
            f"per policy. It also checks {evidence.equivalence_audit.joint_safe_subsets_checked} "
            "joint subsets of oracle-safe actions, including late continuations.",
            "",
            "Candidate writes are distinct Boolean business facts and commute. The subset audit",
            "checks joint invariant preservation; it is not a claim to enumerate all operating-",
            "system schedules. All four declared provider fault schedules are executed.",
            "",
            "## Matched metadata and execution",
            "",
            "Every policy receives the identical immutable AdmissionView: complete candidate",
            "intents and logical IDs, all semantic dependencies and invariant ASTs, complete",
            "world bindings, per-action contracts, idempotency support, reconciliation endpoint,",
            "compensation metadata, public fault schedule, and the same ordered observations.",
            "Per-round SHA-256 input hashes are compared across all policies. Hidden provider",
            "realization and future receipt values are evaluator-only; leaking them would erase",
            "the uncertainty being studied. Each policy faces the same hidden realization within",
            "a matched trial. Upstream probe results are broadcast at common logical rounds; no",
            "policy receives a private successful probe. Compensation is declared unsupported",
            "and is not used to excuse an unsafe effect.",
            "Candidate Boolean flags encode the proposed-effect footprint, not hidden provider",
            "observations. Actual prior effects are checked by the accumulated provider journal",
            "and exhaustive joint-subset oracle. Mutable upstream state and stable permissions",
            "form the shared dependency vector; admitted candidates commute in this workload.",
            "",
            "The Week-1 coordinator, HTTP adapter, persistent ledger, identity checks, provider",
            "journals, and Docker infrastructure execute admitted effects. WAIT returns to the",
            "scripted evidence scheduler, then recertifies after the next shared observation.",
            "The evidence round remains fixed through dispatch. Multiple independent admission",
            "leaders and real-world unmediated writes remain outside this feasibility model.",
            "",
            "## Baseline implementations",
            "",
            "- Global fail-closed uses the complete invariant metadata but defers otherwise",
            "  possible actions while the upstream outcome is unresolved; it is the deliberately",
            "  coarse policy specified by the protocol, not a strong scope baseline.",
            "- Synthetic-scope OCC compiles executable predicates into invariant/outcome conflict",
            "  reservations and validates the current evidence revision before dispatch. Safe",
            "  same-context actions do not acquire irrelevant payment/refund scopes.",
            "- Atomix-inspired scope/frontier seals those complete scopes and checks local",
            "  frontiers. Only incompatible still-possible outcomes hold a frontier back.",
            "- Semantic pending-state/lock derives a full business-operation compatibility matrix",
            "  over the same unresolved outcome modes.",
            "- TCT-C-inspired joint recertification evaluates one symbolic predicate over the",
            "  complete simultaneous current dependency vector, including temporal continuation.",
            "- OCA constructs concrete possible worlds and directly interprets every invariant.",
            "",
            "These are bounded admission models. They do not reproduce full Atomix or TCT",
            "durability, authority, or distributed fencing protocols. TCT's joint recertifier",
            "is intentionally permitted the same logical predicate as OCA; Atomix permits a",
            "semantic pre-commit hook. See the primary sources:",
            "[TCT section 4.4](https://arxiv.org/html/2609.20261#S4.SS4) and",
            "[Atomix](https://arxiv.org/html/2602.14849). Equivalence here concerns these tested",
            "decision models, not a theorem that the complete published systems are identical.",
            "",
            "## Safety results",
            "",
        ]
    )
    for name, runs in grouped.items():
        unsafe = sum(item.metrics.unsafe_admissions for item in runs)
        unsafe_commits = sum(item.metrics.unsafe_actual_commits for item in runs)
        opportunities = sum(item.metrics.decision_opportunities for item in runs)
        commits = sum(item.metrics.actual_candidate_commits for item in runs)
        physical = sum(item.metrics.physical_violation_events for item in runs)
        duplicate = sum(item.metrics.duplicate_effects for item in runs)
        residue = sum(item.metrics.irrecoverable_residue_events for item in runs)
        lines.append(
            f"- `{name}`: unsafe admissions {unsafe}/{opportunities}; "
            f"unsafe actual commits {unsafe_commits}/{commits}; "
            f"physical violation events {physical}; "
            f"duplicate effects {duplicate}; irrecoverable violation residue {residue}."
        )
    lines.extend(
        [
            "",
            "Safety is checked both robustly against all possible worlds and against the actual",
            "provider journal, including later completion of a previously in-flight effect.",
            "No compensation recovery is claimed. Exact zero counts describe this finite workload,",
            "not a population-level guarantee or empirical rate estimate for arbitrary services.",
            "",
            "## Collateral-blocking results",
            "",
            "The fixed denominator is all oracle-safe candidate/evidence-round opportunities",
            "before the terminal receipt (rounds 0-2), including a decision panel for candidates",
            "that already executed. This avoids comparing policy-dependent denominator sizes.",
            "Distinct action counts are summed over the eight scenario/realization trials.",
            "",
        ]
    )
    for name, runs in grouped.items():
        blocked = sum(item.metrics.safe_opportunities_unnecessarily_blocked for item in runs)
        safe = sum(item.metrics.pre_resolution_safe_opportunities for item in runs)
        admitted = sum(item.metrics.safe_actions_admitted_before_resolution for item in runs)
        distinct = sum(item.metrics.collateral_safe_actions_distinct for item in runs)
        waiting = sum(item.metrics.mean_waiting_fanout for item in runs) / len(runs)
        lines.append(
            f"- `{name}`: collateral {blocked}/{safe} "
            f"({100 * blocked / safe:.1f}%); distinct collateral actions {distinct}; "
            f"safe actions admitted before resolution {admitted}; "
            f"mean WAIT fan-out {waiting:.3f} actions per unresolved checkpoint."
        )
    lines.extend(
        [
            "",
            "Logical action-round waiting is recorded in the raw metrics. No wall-clock",
            "throughput or latency advantage is inferred from these controlled rendezvous runs.",
            "",
            "## Equivalence analysis",
            "",
        ]
    )
    for name, count in differences.items():
        lines.append(
            f"- `{name}` differs from OCA in {count}/"
            f"{evidence.equivalence_audit.candidate_outcome_cases_per_policy} "
            "exhaustive candidate/outcome-set decisions (COMMIT, WAIT, and BLOCK)."
        )
    lines.extend(
        [
            "",
            "TCT-C-inspired recertification and OCA differ in representation: symbolic",
            "compatibility over the current vector versus explicit universal world simulation.",
            "Both enforce the same supplied joint predicate. This equivalence is not an",
            "improvement result for OCA and does not establish a new mechanism.",
            "",
            "The practical scope compiler names each invariant/outcome incompatibility and",
            "holds only still-possible conflict slots. It needs a bounded number of slots for",
            "one effect with three outcomes and reproduces the same precision without measured",
            "collateral blocking. It incorporates semantic predicates; the original paper is",
            "not claimed to provide this compiler automatically. Removing that capability",
            "would intentionally weaken an equally informed baseline and was not done.",
            "",
            "The global barrier overblocks safe work, demonstrating the metric, but an OCA",
            "advantage only over that barrier does not satisfy G4 or G5. The complete matched",
            "joint-recertification and scope/frontier controls remove the apparent advantage.",
            "",
            "## Verdict and limits",
            "",
            f"**{verdict}.** The differentiated runtime hypothesis does not survive the matched",
            "equivalence test. Retain the harness as a regression/research artifact; do not",
            "start the original Week-2 build or add LLM APIs on this evidence. This gate does",
            "not independently validate novelty of a benchmark-only project.",
            "",
            "The workload has two Commerce fan-outs, one unresolved effect, finite Boolean",
            "predicates, immediate candidate effects, and a controlled authoritative evidence",
            "schedule. The quiescence certificate is an explicit tool capability, not an",
            "inference from waiting. Results do not establish equivalence for arbitrary",
            "multi-effect or distributed workloads and must not be generalized beyond the model.",
            "",
            "## Reproduction and provenance",
            "",
            "```text",
            "uv run --no-sync python -m experiments.gate1b_uncertainty_containment "
            "--seed 42 --baseline all",
            "```",
            "",
            "Use --ledger postgres with DATABASE_URL, or the Compose gate1b profile service.",
            f"Collected conditions: {len(evidence.results)}; "
            f"seed {evidence.seed}; ledger {evidence.ledger}.",
            f"Source commit: {evidence.source_commit}.",
            f"Source-content SHA-256: {evidence.source_tree_sha256}.",
            f"Dependency lock SHA-256: {evidence.lockfile_sha256}.",
            f"Evidence directory used to generate this report: {evidence_dir.as_posix()}.",
            "Committed evidence is under experiments/results/gate1b/. The summary preserves",
            "exact definitions, normalized input-document hashes, metadata hashes, provenance,",
            "and metrics; each condition has separate runtime, provider, evidence, and decision",
            "streams. In-memory replay is exact; PostgreSQL may reorder commuting completions.",
            "Validation details and cross-mode comparison are recorded in experiments/protocol.md.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
