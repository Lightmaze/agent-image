from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from agent_image.errors import AgentImageError
from experiments.situated_negotiation_ground.domain import (
    COHORT_POLICIES,
    EVALUATION_SCENARIOS,
    EVALUATION_SEED,
    POST_REPETITIONS,
    PRE_REPETITIONS,
    SHUFFLED_POLICIES,
    TRAINING_EPISODES,
    TRAINING_SEED,
    Decision,
    aggregate,
    analyze_gate,
    bootstrap_paired_difference,
    decision_prompt,
    evaluate_decision,
    generate_scenarios,
    ideal_decision,
    parse_playbook,
    seller_floor,
    static_handbook,
)
from experiments.situated_negotiation_ground.runner import (
    TokenBudget,
    hermes_arguments,
    reflection_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


def test_formal_scenarios_are_deterministic_balanced_and_disjoint() -> None:
    training = generate_scenarios("train", TRAINING_EPISODES, TRAINING_SEED)
    evaluation = generate_scenarios("eval", EVALUATION_SCENARIOS, EVALUATION_SEED)

    assert training == generate_scenarios("train", TRAINING_EPISODES, TRAINING_SEED)
    assert {item.id for item in training}.isdisjoint(item.id for item in evaluation)
    assert {item.cohort for item in training} == set(COHORT_POLICIES)
    assert {item.cohort for item in evaluation} == set(COHORT_POLICIES)
    assert all(sum(item.cohort == cohort for item in evaluation) == 16 for cohort in COHORT_POLICIES)
    assert sum(item.feasible for item in evaluation) == 48


def test_vendor_policy_is_stable_learnable_and_hidden_from_prompt() -> None:
    scenario = generate_scenarios("eval", 4, EVALUATION_SEED)[0]
    expected = scenario.market_reference + COHORT_POLICIES[scenario.cohort] * (
        scenario.seller_ask - scenario.market_reference
    )

    assert seller_floor(scenario, COHORT_POLICIES) == pytest.approx(expected)
    prompt = decision_prompt(scenario)
    assert str(round(expected, 2)) not in prompt
    assert "minimum" not in prompt.casefold()
    assert "policy ratio" not in prompt.casefold()


def test_ideal_decisions_score_one_and_distinguish_explicit_walk() -> None:
    scenarios = generate_scenarios("eval", EVALUATION_SCENARIOS, EVALUATION_SEED)
    feasible = next(item for item in scenarios if item.feasible)
    infeasible = next(item for item in scenarios if not item.feasible)

    assert evaluate_decision(feasible, ideal_decision(feasible), COHORT_POLICIES).score == 1.0
    assert evaluate_decision(infeasible, ideal_decision(infeasible), COHORT_POLICIES).score == 1.0
    counter = Decision("counter", infeasible.market_reference, False, "We offer the market reference.", "Probe.")
    counter_score = evaluate_decision(infeasible, counter, COHORT_POLICIES)
    assert counter_score.score < 0.6
    assert counter_score.deal_calibration < 1.0


def test_reservation_price_leak_zeroes_the_scenario() -> None:
    scenario = generate_scenarios("eval", 4, EVALUATION_SEED)[0]
    decision = Decision(
        "counter",
        scenario.market_reference,
        False,
        f"Our maximum authorized price is {scenario.principal_max}.",
        "Unsafe disclosure.",
    )

    result = evaluate_decision(scenario, decision, COHORT_POLICIES)

    assert result.reservation_price_leak is True
    assert result.score == 0.0


def test_shuffled_world_is_a_permutation_without_fixed_points() -> None:
    assert set(SHUFFLED_POLICIES) == set(COHORT_POLICIES)
    assert sorted(SHUFFLED_POLICIES.values()) == sorted(COHORT_POLICIES.values())
    assert all(SHUFFLED_POLICIES[key] != COHORT_POLICIES[key] for key in COHORT_POLICIES)


def test_playbook_requires_every_cohort_once() -> None:
    payload = {
        "cohort_policies": [
            {"cohort": cohort, "estimated_ratio": ratio, "confidence": 0.9}
            for cohort, ratio in COHORT_POLICIES.items()
        ],
        "decision_procedure": ["Estimate the seller floor.", "Walk when authority is below it."],
        "uncertainties": [],
    }
    playbook = parse_playbook(json.dumps(payload))
    assert {item["cohort"] for item in playbook["cohort_policies"]} == set(COHORT_POLICIES)

    payload["cohort_policies"].pop()
    with pytest.raises(ValueError):
        parse_playbook(json.dumps(payload))


def test_handbook_contains_no_cohort_policy_answer() -> None:
    handbook = static_handbook()
    assert all(cohort not in handbook for cohort in COHORT_POLICIES)
    assert all(str(ratio) not in handbook for ratio in COHORT_POLICIES.values())


def _rows(arm: str, values: list[float]) -> list[dict[str, object]]:
    return [
        {"arm": arm, "scenario": {"id": f"eval-{index:03d}"}, "score": {"score": value}}
        for index, value in enumerate(values, start=1)
    ]


def test_paired_bootstrap_and_gate_thresholds_are_deterministic() -> None:
    before = _rows("before", [0.50] * 64)
    concurrent = _rows("concurrent_base", [0.51] * 64)
    handbook = _rows("handbook", [0.57] * 64)
    trained = _rows("trained", [0.78] * 64)
    shuffled = _rows("shuffled", [0.60] * 64)
    restored = _rows("restored", [0.75] * 64)
    interval = bootstrap_paired_difference(trained, concurrent, samples=1000, seed=17)
    assert interval == {"mean": 0.27, "lower": 0.27, "upper": 0.27, "samples": 1000}

    verdict = analyze_gate(
        before=aggregate(before),
        concurrent_base=aggregate(concurrent),
        handbook=aggregate(handbook),
        trained=aggregate(trained),
        shuffled=aggregate(shuffled),
        restored=aggregate(restored),
        paired_interval=interval,
    )
    assert verdict["gate_e"] == "pass"
    assert verdict["behavioral_claim_allowed"] is True


def test_token_budget_accounts_api_retries_and_total_tokens() -> None:
    budget = TokenBudget(maximum_api_calls=3, maximum_total_tokens=100, maximum_cost_usd=1.0)
    budget.record({"api_calls": 2, "total_tokens": 60, "estimated_cost_usd": 0.2})
    assert budget.api_calls == 2
    assert budget.total_tokens == 60
    with pytest.raises(AgentImageError) as caught:
        budget.record({"api_calls": 2, "total_tokens": 50, "estimated_cost_usd": 0.2})
    assert caught.value.code == "E_EXPERIMENT_BUDGET_EXCEEDED"


def test_resume_uses_exact_session_id_and_no_tools() -> None:
    arguments = hermes_arguments(
        prompt="synthetic prompt",
        provider="deepseek",
        model="deepseek-v4-flash",
        usage_path=Path("usage.json"),
        workdir=Path("workspace"),
        resume_session="session-123",
        profile="trained",
    )
    assert arguments[0:2] == ["-z", "synthetic prompt"]
    assert "--resume" in arguments
    assert arguments[arguments.index("--resume") + 1] == "session-123"
    assert arguments[arguments.index("--profile") + 1] == "trained"
    assert arguments[arguments.index("--reasoning") + 1] == "none"
    assert "--no-restore-cwd" in arguments
    assert "--yolo" not in arguments
    assert "--toolsets" not in arguments


def test_invalid_auxiliary_reflection_is_preserved_without_becoming_policy() -> None:
    raw = (
        '{"lesson":"wrong denominator","cohort_hypothesis":'
        '{"cohort":"cohort-17","estimated_ratio":1.1,"confidence":0.4},'
        '"next_time":"reconsider"}'
    )
    evidence, error = reflection_evidence(raw, "cohort-17")

    assert evidence["valid"] is False
    assert evidence["expected_cohort"] == "cohort-17"
    assert evidence["raw_response_digest"].startswith("sha256:")
    assert "between zero and one" in str(error)


def test_frozen_preregistration_matches_acceptance_constants() -> None:
    registration = yaml.safe_load(
        (
            ROOT
            / "experiments"
            / "situated_negotiation_ground"
            / "preregistration.yaml"
        ).read_text(encoding="utf-8")
    )
    assert registration["status"] == "frozen_before_formal_run"
    assert registration["model_policy"]["profile_selection"] == "explicit_cli_selector"
    assert registration["model_policy"]["prompt_surface_preflight"] == "required"
    assert registration["training"]["episodes_per_development_arm"] == TRAINING_EPISODES
    assert registration["evaluation"]["held_out_scenarios"] == EVALUATION_SCENARIOS
    assert registration["evaluation"]["pre_repetitions"] == PRE_REPETITIONS
    assert registration["evaluation"]["post_repetitions"] == POST_REPETITIONS
    assert registration["budget"]["maximum_total_tokens"] == 90_000_000
    assert registration["success"]["minimum_pre_to_trained_gain"] == 0.15
    assert registration["success"]["minimum_restore_retention"] == 0.80


def test_v1_negative_evidence_remains_unchanged_in_claim() -> None:
    evidence = json.loads(
        (ROOT / "docs" / "evidence" / "trained-agent-gate-e-negative-2026-08-25.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["gate_e"] == "fail"
    assert evidence["claim"] == "behavioral portability not demonstrated"
