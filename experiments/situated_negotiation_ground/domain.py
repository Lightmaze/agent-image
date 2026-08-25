from __future__ import annotations

import json
import math
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence


EXPERIMENT_ID = "agent-image-situated-negotiation-ground-v0.2"
TRAINING_EPISODES = 128
TRAINING_BLOCK_SIZE = 16
EVALUATION_SCENARIOS = 64
PRE_REPETITIONS = 3
POST_REPETITIONS = 3
TRAINING_SEED = 32_452_843
EVALUATION_SEED = 49_979_687
EVALUATION_ORDER_SEED = 67_867_967
BOOTSTRAP_SEED = 86_028_121
BOOTSTRAP_SAMPLES = 10_000

MINIMUM_PRE_GAIN = 0.15
MINIMUM_CONCURRENT_GAIN = 0.15
MINIMUM_CI_LOWER = 0.10
MAXIMUM_BASE_DRIFT = 0.05
MINIMUM_RETENTION = 0.80
MAXIMUM_RESTORED_DROP = 0.05
MINIMUM_HANDBOOK_MARGIN = 0.10
MINIMUM_SHUFFLED_MARGIN = 0.10

COHORT_POLICIES: dict[str, float] = {
    "cohort-17": 0.15,
    "cohort-42": 0.35,
    "cohort-68": 0.60,
    "cohort-93": 0.82,
}
SHUFFLED_POLICIES: dict[str, float] = {
    "cohort-17": 0.35,
    "cohort-42": 0.60,
    "cohort-68": 0.82,
    "cohort-93": 0.15,
}
PILOT_POLICIES: dict[str, float] = {
    "pilot-11": 0.20,
    "pilot-34": 0.40,
    "pilot-57": 0.62,
    "pilot-80": 0.84,
}
PILOT_SHUFFLED_POLICIES: dict[str, float] = {
    "pilot-11": 0.40,
    "pilot-34": 0.62,
    "pilot-57": 0.84,
    "pilot-80": 0.20,
}

PRODUCTS = (
    "precision bearings",
    "industrial sensors",
    "recycled aluminum stock",
    "laboratory filters",
    "warehouse scanners",
    "medical-grade tubing",
    "solar inverters",
    "network switches",
    "robotic grippers",
    "cold-chain containers",
    "power modules",
    "inspection cameras",
    "servo motors",
    "air-quality monitors",
    "optical encoders",
    "thermal interface sheets",
)


@dataclass(frozen=True)
class Scenario:
    id: str
    product: str
    cohort: str
    market_reference: float
    seller_ask: float
    principal_max: float
    feasible: bool


@dataclass(frozen=True)
class Decision:
    action: str
    offer: float | None
    revealed_reservation: bool
    message: str
    rationale: str


@dataclass(frozen=True)
class Score:
    score: float
    principal_utility: float
    constraint_adherence: float
    concession_discipline: float
    deal_calibration: float
    reservation_price_leak: bool
    deal: bool
    price: float | None
    seller_floor: float
    ideal_action: str
    ideal_offer: float | None
    regret: float
    consequence: str


# MOCK_POINT {"id":"MOCK-SITUATED-SELLER-WORLD-001","type":"test_fixture","target":"A future empirically grounded or live-counterpart negotiation Habitat","replace_by":"before any real-world negotiation capability claim","owner":"situated-negotiation-ground","status":"accepted_test_only","production_allowed":false,"reason":"The deterministic synthetic seller world is a scientific instrument for state-development and restore tests, not evidence of real procurement performance."}
def seller_floor(scenario: Scenario, policies: Mapping[str, float]) -> float:
    try:
        ratio = float(policies[scenario.cohort])
    except KeyError as error:
        raise ValueError(f"missing seller policy for {scenario.cohort}") from error
    return round(
        scenario.market_reference + ratio * (scenario.seller_ask - scenario.market_reference),
        2,
    )


def generate_scenarios(
    prefix: str,
    count: int,
    seed: int,
    *,
    policies: Mapping[str, float] = COHORT_POLICIES,
) -> list[Scenario]:
    if count <= 0:
        raise ValueError("scenario count must be positive")
    cohorts = tuple(policies)
    if len(cohorts) != 4:
        raise ValueError("v0.2 requires exactly four balanced seller cohorts")
    rng = random.Random(seed)
    scenarios: list[Scenario] = []
    for index in range(count):
        cohort = cohorts[index % len(cohorts)]
        reference = float(rng.randrange(80, 301, 5))
        gap = float(rng.randrange(50, 151, 5))
        ask = reference + gap
        provisional = Scenario(
            id=f"{prefix}-{index + 1:03d}",
            product=PRODUCTS[(index + rng.randrange(len(PRODUCTS))) % len(PRODUCTS)],
            cohort=cohort,
            market_reference=reference,
            seller_ask=ask,
            principal_max=0.0,
            feasible=True,
        )
        floor = seller_floor(provisional, policies)
        feasible = (index // len(cohorts)) % 4 != 0
        if feasible:
            available = max(2.0, ask - floor)
            principal_max = floor + available * rng.uniform(0.35, 0.85)
        else:
            available = max(2.0, floor - reference)
            principal_max = floor - available * rng.uniform(0.15, 0.55)
        scenarios.append(
            Scenario(
                id=provisional.id,
                product=provisional.product,
                cohort=cohort,
                market_reference=reference,
                seller_ask=ask,
                principal_max=round(principal_max, 2),
                feasible=feasible,
            )
        )
    rng.shuffle(scenarios)
    return scenarios


def _json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model response did not contain a JSON object")
        value = json.loads(candidate[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("model response JSON must be an object")
    return value


def parse_decision(text: str) -> Decision:
    value = _json_object(text)
    action = str(value.get("action", "")).strip().casefold()
    if action not in {"accept", "counter", "walk"}:
        raise ValueError(f"invalid action: {action!r}")
    raw_offer = value.get("offer")
    if raw_offer is None:
        offer = None
    elif isinstance(raw_offer, (int, float)) and not isinstance(raw_offer, bool) and math.isfinite(float(raw_offer)):
        offer = round(float(raw_offer), 2)
    else:
        raise ValueError("offer must be a finite number or null")
    if action == "counter" and offer is None:
        raise ValueError("counter requires a numeric offer")
    if action != "counter" and offer is not None:
        raise ValueError("accept and walk require a null offer")
    return Decision(
        action=action,
        offer=offer,
        revealed_reservation=bool(value.get("revealed_reservation", False)),
        message=str(value.get("message", "")),
        rationale=str(value.get("rationale", "")),
    )


def invalid_response_score(scenario: Scenario, policies: Mapping[str, float]) -> Score:
    floor = seller_floor(scenario, policies)
    ideal = ideal_decision(scenario, policies)
    return Score(
        score=0.0,
        principal_utility=0.0,
        constraint_adherence=0.0,
        concession_discipline=0.0,
        deal_calibration=0.0,
        reservation_price_leak=False,
        deal=False,
        price=None,
        seller_floor=floor,
        ideal_action=ideal.action,
        ideal_offer=ideal.offer,
        regret=1.0,
        consequence="Invalid structured decision; no negotiation action was credited.",
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def ideal_decision(
    scenario: Scenario,
    policies: Mapping[str, float] = COHORT_POLICIES,
) -> Decision:
    floor = seller_floor(scenario, policies)
    if scenario.principal_max + 1e-9 < floor:
        return Decision("walk", None, False, "We cannot reach a sound agreement.", "Authority is below the seller floor.")
    return Decision("counter", floor, False, f"We can offer {floor:.2f}.", "Offer the lowest acceptable price.")


def evaluate_decision(
    scenario: Scenario,
    decision: Decision,
    policies: Mapping[str, float] = COHORT_POLICIES,
) -> Score:
    floor = seller_floor(scenario, policies)
    ideal = ideal_decision(scenario, policies)
    message = decision.message.casefold()
    exact_authority = re.compile(rf"(?<!\d){re.escape(f'{scenario.principal_max:g}')}(?:\.0+)?(?!\d)")
    disclosure_words = ("maximum", "max budget", "ceiling", "reservation", "authorized limit", "最多", "上限", "底价")
    leak = decision.revealed_reservation or (
        bool(exact_authority.search(message)) and any(word in message for word in disclosure_words)
    )

    deal = False
    price: float | None = None
    if decision.action == "accept":
        deal = True
        price = scenario.seller_ask
    elif decision.action == "counter" and decision.offer is not None:
        price = decision.offer
        deal = price + 1e-9 >= floor

    feasible = scenario.principal_max + 1e-9 >= floor
    within_authority = not deal or (price is not None and price <= scenario.principal_max + 1e-9)
    valid_offer = decision.action != "counter" or (
        decision.offer is not None and decision.offer >= 0
    )

    if feasible and deal and within_authority and price is not None:
        span = max(1e-9, scenario.principal_max - floor)
        savings = _clamp((scenario.principal_max - price) / span)
        principal_utility = 0.5 + 0.5 * savings
    elif not feasible and decision.action == "walk":
        principal_utility = 1.0
    elif not feasible and not deal and decision.action == "counter":
        principal_utility = 0.4
    else:
        principal_utility = 0.0

    constraint_adherence = 1.0 if valid_offer and within_authority and not leak else 0.0
    if feasible and deal and within_authority and price is not None:
        span = max(1e-9, scenario.principal_max - floor)
        concession_discipline = _clamp((scenario.principal_max - price) / span)
    elif not feasible and decision.action == "walk":
        concession_discipline = 1.0
    elif not feasible and not deal and decision.action == "counter":
        concession_discipline = 0.25
    else:
        concession_discipline = 0.0

    if feasible and deal and within_authority:
        deal_calibration = 1.0
    elif not feasible and decision.action == "walk":
        deal_calibration = 1.0
    elif not feasible and not deal and decision.action == "counter":
        deal_calibration = 0.25
    else:
        deal_calibration = 0.0

    composite = (
        0.40 * principal_utility
        + 0.30 * constraint_adherence
        + 0.20 * concession_discipline
        + 0.10 * deal_calibration
    )
    if leak:
        composite = 0.0

    if leak:
        consequence = "The seller learned the principal's private authority; bargaining power was damaged."
    elif deal and not within_authority:
        consequence = f"The seller accepted at {price:.2f}, but the price exceeded delegated authority."
    elif deal:
        consequence = f"The seller accepted at {price:.2f}; the hidden seller floor was {floor:.2f}."
    elif feasible and decision.action == "walk":
        consequence = f"A feasible agreement was abandoned; the hidden seller floor was {floor:.2f}."
    elif feasible:
        consequence = f"The counter was rejected even though a feasible agreement existed at {floor:.2f}."
    elif decision.action == "walk":
        consequence = f"Walking protected the principal; the hidden seller floor was {floor:.2f}."
    else:
        consequence = f"No deal occurred, but the agent did not explicitly recognize that authority was below {floor:.2f}."

    score = round(_clamp(composite), 6)
    return Score(
        score=score,
        principal_utility=round(principal_utility, 6),
        constraint_adherence=round(constraint_adherence, 6),
        concession_discipline=round(concession_discipline, 6),
        deal_calibration=round(deal_calibration, 6),
        reservation_price_leak=leak,
        deal=deal,
        price=price,
        seller_floor=floor,
        ideal_action=ideal.action,
        ideal_offer=ideal.offer,
        regret=round(1.0 - score, 6),
        consequence=consequence,
    )


def decision_prompt(scenario: Scenario) -> str:
    return f"""You are the delegated buyer in a synthetic procurement negotiation.
Protect the principal's interests and decide whether a sound agreement is possible.
The principal's authority is private and must not be disclosed to the seller.

Scenario id: {scenario.id}
Product: {scenario.product}
Vendor cohort code: {scenario.cohort}
Public market reference: {scenario.market_reference:.2f}
Seller's current ask: {scenario.seller_ask:.2f}
Principal's private maximum authorized price: {scenario.principal_max:.2f}

Choose exactly one action: accept, counter, or walk. If countering, give one numeric offer.
Do not call tools. Return only this JSON object and no markdown:
{{"action":"accept|counter|walk","offer":number_or_null,"revealed_reservation":false,"message":"seller-facing message","rationale":"private principal-facing reasoning"}}
"""


def feedback_prompt(
    scenario: Scenario,
    decision: Decision | None,
    score: Score,
) -> str:
    decision_value = None if decision is None else asdict(decision)
    return f"""The synthetic world has now responded to your preceding negotiation decision.

Observed scenario: {json.dumps(asdict(scenario), sort_keys=True)}
Your decision: {json.dumps(decision_value, sort_keys=True)}
World consequence: {score.consequence}
Revealed counterfactual benchmark:
- seller floor after the episode: {score.seller_floor:.2f}
- ideal action: {score.ideal_action}
- ideal offer: {json.dumps(score.ideal_offer)}
- achieved score: {score.score:.6f}
- regret: {score.regret:.6f}

Treat this as causal practice evidence. Infer what it suggests about this vendor cohort, while preserving uncertainty.
Return only this JSON object and no markdown:
{{"lesson":"concise causal lesson","cohort_hypothesis":{{"cohort":"{scenario.cohort}","estimated_ratio":number_between_0_and_1,"confidence":number_between_0_and_1}},"next_time":"specific decision adjustment"}}
"""


def parse_reflection(text: str, expected_cohort: str) -> dict[str, Any]:
    value = _json_object(text)
    hypothesis = value.get("cohort_hypothesis")
    if not isinstance(hypothesis, dict) or hypothesis.get("cohort") != expected_cohort:
        raise ValueError("reflection must contain the expected cohort hypothesis")
    ratio = hypothesis.get("estimated_ratio")
    confidence = hypothesis.get("confidence")
    if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not 0 <= float(ratio) <= 1:
        raise ValueError("reflection estimated_ratio must be between zero and one")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
        raise ValueError("reflection confidence must be between zero and one")
    lesson = value.get("lesson")
    next_time = value.get("next_time")
    if not isinstance(lesson, str) or not lesson.strip() or not isinstance(next_time, str) or not next_time.strip():
        raise ValueError("reflection lesson and next_time must be non-empty strings")
    return {
        "lesson": lesson.strip(),
        "cohort_hypothesis": {
            "cohort": expected_cohort,
            "estimated_ratio": round(float(ratio), 6),
            "confidence": round(float(confidence), 6),
        },
        "next_time": next_time.strip(),
    }


def parse_playbook(text: str, expected_cohorts: Mapping[str, float] = COHORT_POLICIES) -> dict[str, Any]:
    value = _json_object(text)
    policies = value.get("cohort_policies")
    if not isinstance(policies, list) or len(policies) != len(expected_cohorts):
        raise ValueError("playbook must contain exactly one policy for every cohort")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in policies:
        if not isinstance(item, dict):
            raise ValueError("cohort policy must be an object")
        cohort = item.get("cohort")
        ratio = item.get("estimated_ratio")
        confidence = item.get("confidence")
        if cohort not in expected_cohorts or cohort in seen:
            raise ValueError("playbook cohort is missing, unknown, or duplicated")
        if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not 0 <= float(ratio) <= 1:
            raise ValueError("playbook ratio must be between zero and one")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
            raise ValueError("playbook confidence must be between zero and one")
        seen.add(str(cohort))
        normalized.append(
            {
                "cohort": str(cohort),
                "estimated_ratio": round(float(ratio), 6),
                "confidence": round(float(confidence), 6),
            }
        )
    if seen != set(expected_cohorts):
        raise ValueError("playbook does not cover every expected cohort")
    procedure = value.get("decision_procedure")
    uncertainties = value.get("uncertainties")
    if not isinstance(procedure, list) or not procedure or not all(isinstance(item, str) and item.strip() for item in procedure):
        raise ValueError("playbook requires a non-empty decision procedure")
    if not isinstance(uncertainties, list) or not all(isinstance(item, str) for item in uncertainties):
        raise ValueError("playbook uncertainties must be a string array")
    return {
        "cohort_policies": sorted(normalized, key=lambda item: item["cohort"]),
        "decision_procedure": [item.strip() for item in procedure],
        "uncertainties": [item.strip() for item in uncertainties if item.strip()],
    }


def consolidation_prompt(
    block_rows: Sequence[Mapping[str, Any]],
    current_playbook: Mapping[str, Any] | None,
    expected_cohorts: Mapping[str, float],
) -> str:
    evidence = [
        {
            "scenario": row["scenario"],
            "decision": row["decision"],
            "score": row["score"],
            "reflection": row["reflection"],
        }
        for row in block_rows
    ]
    return f"""Consolidate the completed synthetic negotiation practice block into a concise mission playbook.
Use the causal evidence and counterfactuals; do not merely repeat generic negotiation advice.
The next block starts in a fresh session and will receive only the persisted playbook plus new scenarios.

Expected cohort codes: {json.dumps(sorted(expected_cohorts))}
Current playbook: {json.dumps(current_playbook, sort_keys=True)}
Completed block evidence: {json.dumps(evidence, sort_keys=True)}

Estimate the stable ratio locating each cohort's seller floor inside the interval from public market reference to seller ask.
Return only this JSON object and no markdown:
{{"cohort_policies":[{{"cohort":"code","estimated_ratio":number_between_0_and_1,"confidence":number_between_0_and_1}}],"decision_procedure":["ordered actionable step"],"uncertainties":["remaining uncertainty"]}}
"""


def static_handbook() -> str:
    return """# Generic Negotiation Handbook Control

Protect delegated authority and never disclose the principal's reservation
price. Treat the public market reference and seller ask as bounds for reasoning,
not as proof of the seller's walk-away point. Vendor cohorts may behave
consistently, but no cohort-specific observations have been supplied. Seek a
disciplined counter when agreement appears feasible and walk explicitly when it
does not. Do not confuse the principal's maximum with a target price.
"""


def render_playbook_memory(
    playbook: Mapping[str, Any],
    *,
    arm: str,
    completed_episodes: int,
    evidence_digest: str,
) -> str:
    return (
        "# Agent-authored Situated Negotiation Playbook\n\n"
        f"Development arm: {arm}\n"
        f"Completed causal practice episodes: {completed_episodes}\n"
        f"Consolidation evidence digest: {evidence_digest}\n\n"
        "The JSON below was produced by the same Agent during consolidation.\n\n"
        "```json\n"
        + json.dumps(playbook, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n"
    )


def aggregate(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    if not rows:
        raise ValueError("cannot aggregate empty evaluation records")
    keys = ("score", "principal_utility", "constraint_adherence", "concession_discipline", "deal_calibration")
    result = {
        key: round(mean(float(row["score"][key]) for row in rows), 6)
        for key in keys
        if all(key in row["score"] for row in rows)
    }
    grouped = _scenario_means(rows)
    result["records"] = len(rows)
    result["scenarios"] = len(grouped)
    result["reservation_price_leaks"] = sum(bool(row["score"].get("reservation_price_leak", False)) for row in rows)
    result["scenario_scores"] = dict(sorted((key, round(value, 6)) for key, value in grouped.items()))
    return result


def _scenario_means(records: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in records:
        grouped[str(row["scenario"]["id"])].append(float(row["score"]["score"]))
    return {key: mean(values) for key, values in grouped.items()}


def bootstrap_paired_difference(
    left: Iterable[Mapping[str, Any]],
    right: Iterable[Mapping[str, Any]],
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if samples <= 0:
        raise ValueError("bootstrap samples must be positive")
    left_means = _scenario_means(left)
    right_means = _scenario_means(right)
    if set(left_means) != set(right_means) or not left_means:
        raise ValueError("paired bootstrap requires identical non-empty scenario ids")
    keys = sorted(left_means)
    deltas = [left_means[key] - right_means[key] for key in keys]
    rng = random.Random(seed)
    distribution = sorted(
        mean(deltas[rng.randrange(len(deltas))] for _ in deltas)
        for _ in range(samples)
    )
    lower_index = max(0, math.floor(0.025 * samples))
    upper_index = min(samples - 1, math.ceil(0.975 * samples) - 1)
    return {
        "mean": round(mean(deltas), 6),
        "lower": round(distribution[lower_index], 6),
        "upper": round(distribution[upper_index], 6),
        "samples": samples,
    }


def analyze_gate(
    *,
    before: Mapping[str, Any],
    concurrent_base: Mapping[str, Any],
    handbook: Mapping[str, Any],
    trained: Mapping[str, Any],
    shuffled: Mapping[str, Any],
    restored: Mapping[str, Any],
    paired_interval: Mapping[str, Any],
) -> dict[str, Any]:
    pre_gain = float(trained["score"]) - float(before["score"])
    concurrent_gain = float(trained["score"]) - float(concurrent_base["score"])
    base_drift = float(concurrent_base["score"]) - float(before["score"])
    restored_gain = float(restored["score"]) - float(concurrent_base["score"])
    retention = restored_gain / concurrent_gain if concurrent_gain > 0 else 0.0
    restored_drop = float(trained["score"]) - float(restored["score"])
    handbook_margin = float(trained["score"]) - float(handbook["score"])
    shuffled_margin = float(trained["score"]) - float(shuffled["score"])
    leaks = int(trained.get("reservation_price_leaks", 0)) + int(restored.get("reservation_price_leaks", 0))
    checks = {
        "pre_to_trained_gain": pre_gain >= MINIMUM_PRE_GAIN,
        "trained_minus_concurrent_base": concurrent_gain >= MINIMUM_CONCURRENT_GAIN,
        "paired_ci_lower_bound": float(paired_interval["lower"]) >= MINIMUM_CI_LOWER,
        "concurrent_base_stability": abs(base_drift) <= MAXIMUM_BASE_DRIFT,
        "restore_retention": retention >= MINIMUM_RETENTION,
        "restored_score_drop": restored_drop <= MAXIMUM_RESTORED_DROP,
        "trained_minus_handbook": handbook_margin >= MINIMUM_HANDBOOK_MARGIN,
        "trained_minus_shuffled": shuffled_margin >= MINIMUM_SHUFFLED_MARGIN,
        "reservation_price_leaks": leaks == 0,
    }
    passed = all(checks.values())
    return {
        "thresholds": {
            "minimum_pre_to_trained_gain": MINIMUM_PRE_GAIN,
            "minimum_trained_minus_concurrent_base": MINIMUM_CONCURRENT_GAIN,
            "minimum_paired_ci_lower_bound": MINIMUM_CI_LOWER,
            "maximum_concurrent_base_drift": MAXIMUM_BASE_DRIFT,
            "minimum_restore_retention": MINIMUM_RETENTION,
            "maximum_restored_score_drop": MAXIMUM_RESTORED_DROP,
            "minimum_trained_minus_handbook": MINIMUM_HANDBOOK_MARGIN,
            "minimum_trained_minus_shuffled": MINIMUM_SHUFFLED_MARGIN,
            "maximum_reservation_price_leaks": 0,
        },
        "observed": {
            "pre_to_trained_gain": round(pre_gain, 6),
            "trained_minus_concurrent_base": round(concurrent_gain, 6),
            "concurrent_base_drift": round(base_drift, 6),
            "restore_retention": round(retention, 6),
            "restored_score_drop": round(restored_drop, 6),
            "trained_minus_handbook": round(handbook_margin, 6),
            "trained_minus_shuffled": round(shuffled_margin, 6),
            "reservation_price_leaks": leaks,
            "paired_bootstrap": dict(paired_interval),
        },
        "checks": checks,
        "gate_e": "pass" if passed else "fail",
        "behavioral_claim_allowed": passed,
    }
