"""Matched-denominator containment metrics for Gate 1B decision panels."""

from pydantic import BaseModel

from agenttxn.effects.models import Decision


class DecisionSample(BaseModel):
    round: int
    candidate_id: str
    input_sha256: str
    possible_outcomes: tuple[str, ...]
    oracle_safe: bool
    decision: Decision
    already_executed: bool
    reason: str
    coordination_scopes: tuple[str, ...] = ()
    blocked_scopes: tuple[str, ...] = ()


class ContainmentMetrics(BaseModel):
    decision_opportunities: int
    unsafe_admissions: int
    unsafe_admission_rate: float
    unsafe_actual_commits: int
    unsafe_commit_rate: float
    actual_candidate_commits: int
    physical_violation_events: int
    physical_state_checks: int
    invariant_violation_rate: float
    duplicate_effects: int
    duplicate_effect_rate: float
    irrecoverable_residue_events: int
    pre_resolution_safe_opportunities: int
    safe_opportunities_unnecessarily_blocked: int
    collateral_block_rate: float
    collateral_safe_actions_distinct: int
    safe_actions_admitted_before_resolution: int
    uncertainty_blast_radius: int
    mean_waiting_fanout: float
    irrelevant_wait_action_rounds: int


def containment_metrics(
    panel: list[DecisionSample],
    committed_ids: list[str],
    violations: int,
) -> ContainmentMetrics:
    unresolved = [item for item in panel if item.round < 3]
    safe = [item for item in unresolved if item.oracle_safe]
    collateral = [item for item in safe if item.decision != Decision.COMMIT]
    unsafe = sum(item.decision == Decision.COMMIT and not item.oracle_safe for item in panel)
    unsafe_executed = sum(
        item.decision == Decision.COMMIT and not item.oracle_safe and not item.already_executed
        for item in panel
    )
    unique_commits = set(committed_ids)
    return ContainmentMetrics(
        decision_opportunities=len(panel),
        unsafe_admissions=unsafe,
        unsafe_admission_rate=unsafe / len(panel) if panel else 0.0,
        unsafe_actual_commits=unsafe_executed,
        unsafe_commit_rate=unsafe_executed / len(committed_ids) if committed_ids else 0.0,
        actual_candidate_commits=len(committed_ids),
        physical_violation_events=violations,
        physical_state_checks=len(committed_ids) + 4,
        invariant_violation_rate=violations / (len(committed_ids) + 4),
        duplicate_effects=len(committed_ids) - len(unique_commits),
        duplicate_effect_rate=(len(committed_ids) - len(unique_commits)) / len(committed_ids)
        if committed_ids
        else 0.0,
        irrecoverable_residue_events=violations,
        pre_resolution_safe_opportunities=len(safe),
        safe_opportunities_unnecessarily_blocked=len(collateral),
        collateral_block_rate=len(collateral) / len(safe) if safe else 0.0,
        collateral_safe_actions_distinct=len({item.candidate_id for item in collateral}),
        safe_actions_admitted_before_resolution=len(
            {item.candidate_id for item in safe if item.decision == Decision.COMMIT}
        ),
        uncertainty_blast_radius=sum(
            item.round == 0 and item.decision == Decision.WAIT for item in panel
        ),
        mean_waiting_fanout=sum(item.decision == Decision.WAIT for item in unresolved) / 3,
        irrelevant_wait_action_rounds=len(collateral),
    )
