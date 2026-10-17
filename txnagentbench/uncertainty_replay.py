"""Reevaluate saved Gate-1B evidence without contacting a provider or database."""

import json
from pathlib import Path

from agenttxn.effects.models import Operation
from agenttxn.effects.outcomes import ExternalOutcome
from agenttxn.metrics.collateral import DecisionSample, containment_metrics
from agenttxn.runtime.outcome_admission import view_hash
from agenttxn.runtime.uncertainty import AdmissionView, MatchedProblem, Observation
from txnagentbench.oracle import oracle_safe, violations
from txnagentbench.uncertainty_runner import UncertaintyRun


def verify_summary(directory: Path) -> int:
    manifest = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    definitions = {
        item["scenario_id"]: MatchedProblem.model_validate(item) for item in manifest["scenarios"]
    }
    matched: dict[tuple[str, str], tuple[str, ...]] = {}
    checked = 0
    for raw in manifest["results"]:
        result = UncertaintyRun.model_validate(raw)
        key = result.scenario_id, str(result.realization)
        if key in matched and matched[key] != result.input_hashes:
            raise ValueError("Saved baseline inputs are not matched")
        matched[key] = result.input_hashes
        problem = definitions[result.scenario_id]
        candidates = {item.intent.effect_id: item for item in problem.candidates}
        rows = [
            json.loads(line) for line in (directory / result.trace_file).read_text().splitlines()
        ]
        panel = [
            DecisionSample.model_validate(row) for row in rows if row["kind"] == "decision_panel"
        ]
        evidence = [
            Observation.model_validate(row["observation"])
            for row in rows
            if row["kind"] == "evidence"
        ]
        for item in panel:
            view = AdmissionView(problem=problem, observations=tuple(evidence[: item.round + 1]))
            if item.input_sha256 != view_hash(view):
                raise ValueError("Input hash differs from saved complete metadata and observations")
            if item.oracle_safe != oracle_safe(
                problem, candidates[item.candidate_id], view.outcomes
            ):
                raise ValueError("Saved possible-world oracle verdict differs from replay")
        provider = [row for row in rows if row["kind"] == "provider_commit"]
        commits = [
            row["request"]["action_name"]
            for row in provider
            if row["operation"] == Operation.CANDIDATE
        ]
        # Independently rebuild physical checks at each observed provider checkpoint.
        prior: set[str] = set()
        physical: list[dict[str, object]] = []
        for checkpoint in (row for row in rows if row["kind"] == "provider_checkpoint"):
            round_number = checkpoint["round"]
            outcome = checkpoint["real_outcome"]
            external = ExternalOutcome(outcome)
            bad = violations(problem, tuple(candidates[name] for name in sorted(prior)), external)
            if bad:
                physical.append(
                    {"round": round_number, "kind": "upstream_resolution", "violations": list(bad)}
                )
            prefix = provider[: checkpoint["provider_journal_length"]]
            for row in prefix:
                if row["operation"] != Operation.CANDIDATE:
                    continue
                name = row["request"]["action_name"]
                if name not in prior:
                    prior.add(name)
                    bad = violations(
                        problem, tuple(candidates[item] for item in sorted(prior)), external
                    )
                    if bad:
                        physical.append(
                            {
                                "round": round_number,
                                "kind": "candidate_commit",
                                "candidate": name,
                                "violations": list(bad),
                            }
                        )
            if sorted(prior) != checkpoint["candidate_commit_ids"]:
                raise ValueError("Provider checkpoint does not match its committed-effect prefix")
        saved_physical = [
            {
                **{
                    key: value
                    for key, value in row.items()
                    if key not in {"kind", "violation_kind"}
                },
                "kind": row["violation_kind"],
            }
            for row in rows
            if row["kind"] == "physical_violation"
        ]
        if saved_physical != physical:
            raise ValueError("Physical violation count differs from provider replay")
        replay = containment_metrics(panel, commits, len(physical))
        if replay != result.metrics:
            raise ValueError("Reported metrics differ from raw trace replay")
        checked += 1
    return checked
