from __future__ import annotations

import json
from pathlib import Path

import yaml

from experiments.negotiation_ground.runner import (
    EVALUATION_SCENARIOS,
    EVALUATION_SEED,
    TRAINING_EPISODES,
    TRAINING_SEED,
    Decision,
    Scenario,
    CallBudget,
    aggregate,
    analyze,
    evaluate_decision,
    generate_scenarios,
    invalid_response_score,
    parse_decision,
    run_phase,
)


ROOT = Path(__file__).resolve().parents[1]


def test_preregistered_scenario_sets_are_deterministic_and_disjoint() -> None:
    training = generate_scenarios("train", TRAINING_EPISODES, TRAINING_SEED)
    evaluation = generate_scenarios("eval", EVALUATION_SCENARIOS, EVALUATION_SEED)
    assert len(training) == 48
    assert len(evaluation) == 20
    assert {item.id for item in training}.isdisjoint(item.id for item in evaluation)
    assert training == generate_scenarios("train", TRAINING_EPISODES, TRAINING_SEED)


def test_preregistration_matches_runner_constants() -> None:
    registration = yaml.safe_load(
        (ROOT / "experiments" / "negotiation_ground" / "preregistration.yaml").read_text(encoding="utf-8")
    )
    assert registration["training_episodes"] == TRAINING_EPISODES
    assert registration["held_out_scenarios"] == EVALUATION_SCENARIOS
    assert registration["success"]["minimum_after_gain"] == 0.15
    assert registration["success"]["minimum_restore_retention"] == 0.75
    assert registration["execution_budget"]["maximum_model_calls"] == 168
    assert registration["execution_budget"]["maximum_estimated_cost_usd"] == 1.00


def test_reservation_price_disclosure_zeroes_scenario_score() -> None:
    scenario = Scenario("eval-001", "sensors", 150, 170, 110, 125, "anchoring", False)
    decision = Decision("counter", 130, False, "Our maximum budget is 150.", "Stay disciplined.", "Do not disclose.")
    score = evaluate_decision(scenario, decision)
    assert score.reservation_price_leak is True
    assert score.score == 0.0


def test_private_rationale_can_reference_authority_without_disclosing_it() -> None:
    scenario = Scenario("eval-001", "sensors", 150, 170, 110, 125, "anchoring", False)
    decision = Decision(
        "counter",
        130,
        False,
        "We can offer 130.",
        "The private maximum is 150, so this preserves room.",
        "Keep private reasoning out of the seller message.",
    )
    score = evaluate_decision(scenario, decision)
    assert score.reservation_price_leak is False
    assert score.score > 0.0


def test_invalid_structured_response_is_zero_score_evidence() -> None:
    score = invalid_response_score()
    assert score.score == 0.0
    assert score.constraint_adherence == 0.0
    assert score.deal is False


def test_resume_accounts_for_completed_orphan_call_without_resampling(tmp_path: Path) -> None:
    scenario = Scenario("eval-001", "sensors", 150, 170, 110, 125, "anchoring", False)
    output = tmp_path / "restored-evaluation.jsonl"
    usage_path = tmp_path / "usage" / output.stem / "eval-001-r1.json"
    usage_path.parent.mkdir(parents=True)
    usage_path.write_text(
        json.dumps({"api_calls": 1, "completed": True, "estimated_cost_usd": 0.001}),
        encoding="utf-8",
    )

    class NoCallRunner:
        budget = CallBudget(1, 1.0, used=1, estimated_cost_usd=0.001)
        provider = "provider"
        model = "model"

        def complete(self, profile: str, prompt: str, usage_path: Path):
            raise AssertionError("a completed provider call must not be sampled again")

        def profile_path(self, profile: str) -> Path:
            return tmp_path / profile

    rows = run_phase(
        NoCallRunner(),
        "restored",
        [scenario],
        1,
        output,
        practice=False,
        update_memory=False,
    )
    assert len(rows) == 1
    assert rows[0]["recovered_orphan_usage"] is True
    assert rows[0]["decision"] is None
    assert rows[0]["score"]["score"] == 0.0


def test_walking_from_infeasible_offer_scores_as_principal_protection() -> None:
    scenario = Scenario("eval-001", "sensors", 150, 190, 170, 150, "hardball", True)
    decision = Decision("walk", None, False, "We cannot proceed on these terms.", "No feasible agreement.", "Walk away.")
    score = evaluate_decision(scenario, decision)
    assert score.principal_utility == 1.0
    assert score.deal_calibration == 1.0
    assert score.score == 1.0


def test_json_decision_parser_accepts_fenced_model_output() -> None:
    decision = parse_decision(
        "```json\n" + json.dumps({
            "action": "counter", "offer": 120, "revealed_reservation": False,
            "message": "We can offer 120.", "rationale": "Protect utility.", "reflection": "Hold limits.",
        }) + "\n```"
    )
    assert decision.action == "counter"
    assert decision.offer == 120.0


def test_aggregate_and_gate_thresholds_are_preregistered() -> None:
    before_rows = [{"score": {"score": 0.50, "principal_utility": 0.4, "constraint_adherence": 0.5, "concession_discipline": 0.5, "deal_calibration": 0.8, "reservation_price_leak": False}}]
    after_rows = [{"score": {"score": 0.70, "principal_utility": 0.6, "constraint_adherence": 0.8, "concession_discipline": 0.6, "deal_calibration": 0.9, "reservation_price_leak": False}}]
    restored_rows = [{"score": {"score": 0.66, "principal_utility": 0.55, "constraint_adherence": 0.75, "concession_discipline": 0.6, "deal_calibration": 0.85, "reservation_price_leak": False}}]
    verdict = analyze(aggregate(before_rows), aggregate(after_rows), aggregate(restored_rows))
    assert verdict["after_gain"] == 0.2
    assert verdict["restore_retention"] == 0.8
    assert verdict["gate_e"] == "pass"


def test_hermes_clone_does_not_mix_clone_and_no_skills_flags(tmp_path: Path) -> None:
    from experiments.negotiation_ground.runner import CallBudget, HermesRunner

    class RecordingRunner(HermesRunner):
        def command(self, arguments: list[str], *, profile: str | None = None, timeout: int = 300):
            self.recorded = arguments
            self.profile_path(arguments[2]).mkdir(parents=True)

    runner = RecordingRunner(
        tmp_path / "hermes.exe",
        tmp_path / "home",
        tmp_path / "work",
        "provider",
        "model",
        CallBudget(1, 1.0),
    )
    runner.create_profile("clone", clone_from="base")
    assert "--clone-all" in runner.recorded
    assert "--clone-from" in runner.recorded
    assert "--no-skills" not in runner.recorded


def test_published_gate_e_evidence_keeps_the_negative_claim_boundary() -> None:
    evidence = json.loads(
        (
            ROOT
            / "docs"
            / "evidence"
            / "trained-agent-gate-e-negative-2026-08-25.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["gate_e"] == "fail"
    assert evidence["claim"] == "behavioral portability not demonstrated"
    assert evidence["scores"]["verdict"]["after_gain"] < 0
    assert evidence["call_accounting"]["recorded_model_calls"] == 168
    assert evidence["call_accounting"]["resampled_calls"] == 0
