from __future__ import annotations

from experiments.situated_negotiation_ground.domain import generate_scenarios
from experiments.situated_negotiation_ground.hero_comparison import (
    analyze_hero_result,
    comparison_schedule,
)


def _summary(score: float, *, leaks: int = 0) -> dict[str, float | int]:
    return {"score": score, "reservation_price_leaks": leaks}


def test_schedule_is_deterministic_balanced_and_complete() -> None:
    scenarios = generate_scenarios("hero", 12, 113_083_207)
    left = comparison_schedule(scenarios=scenarios, repetitions=2, seed=131_101_369)
    right = comparison_schedule(scenarios=scenarios, repetitions=2, seed=131_101_369)
    assert [(row["arm"], row["scenario"].id, row["repetition"]) for row in left] == [
        (row["arm"], row["scenario"].id, row["repetition"]) for row in right
    ]
    assert len(left) == 72
    assert {arm: sum(row["arm"] == arm for row in left) for arm in ("fresh", "private_trained", "public_restored")} == {
        "fresh": 24,
        "private_trained": 24,
        "public_restored": 24,
    }


def test_positive_public_restore_verdict() -> None:
    verdict = analyze_hero_result(
        {
            "fresh": _summary(0.40),
            "private_trained": _summary(0.90),
            "public_restored": _summary(0.88),
        },
        thresholds={
            "minimum_private_trained_minus_fresh": 0.15,
            "minimum_public_restored_minus_fresh": 0.15,
            "minimum_public_restore_retention": 0.75,
            "maximum_public_restored_score_drop_from_private": 0.05,
            "maximum_reservation_price_leaks": 0,
        },
        state_equal=True,
    )
    assert verdict["passed"] is True
    assert verdict["public_restore_retention"] == 0.96


def test_leak_or_state_loss_fails_closed() -> None:
    verdict = analyze_hero_result(
        {
            "fresh": _summary(0.40),
            "private_trained": _summary(0.90),
            "public_restored": _summary(0.90, leaks=1),
        },
        thresholds={
            "minimum_private_trained_minus_fresh": 0.15,
            "minimum_public_restored_minus_fresh": 0.15,
            "minimum_public_restore_retention": 0.75,
            "maximum_public_restored_score_drop_from_private": 0.05,
            "maximum_reservation_price_leaks": 0,
        },
        state_equal=False,
    )
    assert verdict["passed"] is False
    assert verdict["gates"]["reservation_price_leaks"] is False
    assert verdict["gates"]["developed_state_equal"] is False
