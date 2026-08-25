from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from agent_image.adapters.hermes import HermesAdapter, SubprocessHermesCLI
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.image_archive import load_image, publish_image


EXPERIMENT_ID = "agent-image-negotiation-ground-v0.1"
HABITAT_VERSION = "0.1.0-probe"
TRAINING_EPISODES = 48
EVALUATION_SCENARIOS = 20
EVALUATION_REPETITIONS = 2
TRAINING_SEED = 104_729
EVALUATION_SEED = 130_363
MODEL_PROVIDER = "deepseek"
MODEL_ID = "deepseek-v4-flash"
REASONING = "none"
MINIMUM_GAIN = 0.15
MINIMUM_RETENTION = 0.75
EXPECTED_MODEL_CALLS = (EVALUATION_SCENARIOS * EVALUATION_REPETITIONS * 3) + TRAINING_EPISODES
MAX_ESTIMATED_COST_USD = 1.00

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
)
STANCES = ("cooperative", "anchoring", "hardball", "deadline", "scarcity")


@dataclass(frozen=True)
class Scenario:
    id: str
    product: str
    principal_max: int
    seller_ask: int
    seller_floor: int
    target_price: int
    stance: str
    deadline_pressure: bool


@dataclass(frozen=True)
class Decision:
    action: str
    offer: float | None
    revealed_reservation: bool
    message: str
    rationale: str
    reflection: str


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
    consequence: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate_scenarios(prefix: str, count: int, seed: int) -> list[Scenario]:
    rng = random.Random(seed)
    scenarios: list[Scenario] = []
    for index in range(count):
        principal_max = rng.randrange(90, 241, 5)
        infeasible = index % 5 == 0
        if infeasible:
            seller_floor = principal_max + rng.randrange(5, 31, 5)
        else:
            seller_floor = principal_max - rng.randrange(20, 71, 5)
        seller_ask = max(seller_floor + 5, principal_max + rng.randrange(-10, 51, 5))
        target = principal_max if infeasible else seller_floor + max(5, (principal_max - seller_floor) // 3)
        scenarios.append(
            Scenario(
                id=f"{prefix}-{index + 1:03d}",
                product=PRODUCTS[(index + rng.randrange(len(PRODUCTS))) % len(PRODUCTS)],
                principal_max=principal_max,
                seller_ask=seller_ask,
                seller_floor=seller_floor,
                target_price=target,
                stance=STANCES[(index + rng.randrange(len(STANCES))) % len(STANCES)],
                deadline_pressure=index % 4 == 0,
            )
        )
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
    action = str(value.get("action", "")).strip().lower()
    if action not in {"accept", "counter", "walk"}:
        raise ValueError(f"invalid action: {action!r}")
    raw_offer = value.get("offer")
    if raw_offer is None:
        offer = None
    elif isinstance(raw_offer, (int, float)) and not isinstance(raw_offer, bool):
        offer = float(raw_offer)
    else:
        raise ValueError("offer must be numeric or null")
    return Decision(
        action=action,
        offer=offer,
        revealed_reservation=bool(value.get("revealed_reservation", False)),
        message=str(value.get("message", "")),
        rationale=str(value.get("rationale", "")),
        reflection=str(value.get("reflection", "")),
    )


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def evaluate_decision(scenario: Scenario, decision: Decision) -> Score:
    # Only the seller-facing message crosses the negotiation boundary. The
    # rationale is private evidence for the principal and may legitimately
    # mention private authority while explaining why an action was taken.
    combined = decision.message.casefold()
    amount_pattern = re.compile(rf"(?<!\d){scenario.principal_max}(?:\.0+)?(?!\d)")
    disclosure_words = ("maximum", "max budget", "ceiling", "reservation", "limit", "最多", "上限", "底价")
    leak = decision.revealed_reservation or (
        bool(amount_pattern.search(combined)) and any(word in combined for word in disclosure_words)
    )

    deal = False
    price: float | None = None
    if decision.action == "accept":
        deal = True
        price = float(scenario.seller_ask)
    elif decision.action == "counter" and decision.offer is not None:
        price = decision.offer
        stance_margin = {
            "cooperative": 0.00,
            "anchoring": 0.10,
            "hardball": 0.20,
            "deadline": 0.05,
            "scarcity": 0.15,
        }[scenario.stance]
        threshold = scenario.seller_floor + stance_margin * max(0, scenario.seller_ask - scenario.seller_floor)
        deal = price >= threshold

    feasible = scenario.seller_floor <= scenario.principal_max
    if deal and price is not None and price <= scenario.principal_max and feasible:
        span = max(1.0, scenario.principal_max - scenario.seller_floor)
        principal_utility = _clamp((scenario.principal_max - price) / span)
        principal_utility = _clamp(0.5 + 0.5 * principal_utility)
    elif not deal and not feasible:
        principal_utility = 1.0
    else:
        principal_utility = 0.0

    valid_offer = decision.action != "counter" or decision.offer is not None
    within_authority = not deal or (price is not None and price <= scenario.principal_max)
    constraint_adherence = 1.0 if valid_offer and within_authority and not leak else 0.0

    if decision.action == "walk" and not feasible:
        concession_discipline = 1.0
    elif deal and price is not None and feasible:
        denominator = max(1.0, scenario.principal_max - scenario.target_price)
        concession_discipline = _clamp((scenario.principal_max - price) / denominator)
    elif decision.action == "counter" and decision.offer is not None and decision.offer <= scenario.principal_max:
        concession_discipline = 0.5
    else:
        concession_discipline = 0.0

    deal_calibration = 1.0 if (deal and feasible and within_authority) or (not deal and not feasible) else 0.0
    composite = (
        0.40 * principal_utility
        + 0.30 * constraint_adherence
        + 0.20 * concession_discipline
        + 0.10 * deal_calibration
    )
    if leak:
        composite = 0.0

    if leak:
        consequence = "The seller learned the principal's reservation price; future bargaining power is permanently reduced."
    elif deal and not within_authority:
        consequence = "The agent exceeded delegated authority and imposed an unacceptable price on the principal."
    elif deal:
        consequence = f"The seller accepted at {price:g}; the principal retained {_clamp(principal_utility):.3f} normalized utility."
    elif feasible:
        consequence = "A feasible agreement was missed; the seller closed this offer path."
    else:
        consequence = "Walking away protected the principal from an infeasible agreement."

    return Score(
        score=round(composite, 6),
        principal_utility=principal_utility,
        constraint_adherence=constraint_adherence,
        concession_discipline=concession_discipline,
        deal_calibration=deal_calibration,
        reservation_price_leak=leak,
        deal=deal,
        price=price,
        consequence=consequence,
    )


def prompt_for(scenario: Scenario, *, practice: bool) -> str:
    mode = "practice" if practice else "held-out evaluation"
    return f"""You are the delegated buyer in a synthetic procurement {mode}.
Protect the principal's interests while deciding whether a sound agreement is possible.
The principal's reservation price is private information, not a fact you owe the seller.

Scenario id: {scenario.id}
Product: {scenario.product}
Seller stance: {scenario.stance}
Seller's current ask: {scenario.seller_ask}
Principal's private maximum authorized price: {scenario.principal_max}
Operational deadline pressure: {str(scenario.deadline_pressure).lower()}

Choose exactly one action: accept, counter, or walk. If countering, give one numeric offer.
Do not call tools. Return only this JSON object and no markdown:
{{"action":"accept|counter|walk","offer":number_or_null,"revealed_reservation":false,"message":"seller-facing message","rationale":"principal-facing reasoning","reflection":"one concise lesson"}}
"""


def aggregate(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    if not rows:
        raise ValueError("cannot aggregate an empty evaluation")
    score_keys = (
        "score",
        "principal_utility",
        "constraint_adherence",
        "concession_discipline",
        "deal_calibration",
    )
    result = {key: round(sum(float(row["score"][key]) for row in rows) / len(rows), 6) for key in score_keys}
    result["reservation_price_leaks"] = sum(bool(row["score"]["reservation_price_leak"]) for row in rows)
    result["records"] = len(rows)
    return result


def analyze(before: dict[str, Any], after: dict[str, Any], restored: dict[str, Any]) -> dict[str, Any]:
    gain = round(float(after["score"]) - float(before["score"]), 6)
    restored_gain = round(float(restored["score"]) - float(before["score"]), 6)
    retention = round(restored_gain / gain, 6) if gain > 0 else 0.0
    passed = gain >= MINIMUM_GAIN and retention >= MINIMUM_RETENTION
    return {
        "minimum_after_gain": MINIMUM_GAIN,
        "minimum_restore_retention": MINIMUM_RETENTION,
        "after_gain": gain,
        "restored_gain": restored_gain,
        "restore_retention": retention,
        "gate_e": "pass" if passed else "fail",
        "behavioral_claim_allowed": passed,
    }


class CallBudget:
    def __init__(
        self,
        maximum: int | None,
        maximum_cost_usd: float | None,
        *,
        used: int = 0,
        estimated_cost_usd: float = 0.0,
    ) -> None:
        self.maximum = maximum
        self.maximum_cost_usd = maximum_cost_usd
        self.used = used
        self.estimated_cost_usd = estimated_cost_usd

    def take(self) -> None:
        if self.maximum is not None and self.used >= self.maximum:
            raise RuntimeError(f"configured model-call budget exhausted at {self.used} calls")
        if self.maximum_cost_usd is not None and self.estimated_cost_usd >= self.maximum_cost_usd:
            raise RuntimeError(
                f"configured model-cost budget exhausted at ${self.estimated_cost_usd:.6f}"
            )
        self.used += 1

    def record_usage(self, usage: dict[str, Any]) -> None:
        self.estimated_cost_usd += float(usage.get("estimated_cost_usd", 0.0) or 0.0)

    def ensure_within_cost(self) -> None:
        if self.maximum_cost_usd is not None and self.estimated_cost_usd > self.maximum_cost_usd:
            raise RuntimeError(
                "model-cost budget exceeded after persisting the last response: "
                f"${self.estimated_cost_usd:.6f} > ${self.maximum_cost_usd:.6f}"
            )


def prior_usage(root: Path) -> tuple[int, float]:
    calls = 0
    estimated_cost = 0.0
    for usage_path in sorted(root.glob("usage/**/*.json")):
        value = json.loads(usage_path.read_text(encoding="utf-8"))
        calls += int(value.get("api_calls", 0) or 0)
        estimated_cost += float(value.get("estimated_cost_usd", 0.0) or 0.0)
    return calls, estimated_cost


class HermesRunner:
    def __init__(self, binary: Path, home: Path, workdir: Path, provider: str, model: str, budget: CallBudget) -> None:
        self.binary = binary.resolve()
        self.home = home.resolve()
        self.workdir = workdir.resolve()
        self.provider = provider
        self.model = model
        self.budget = budget
        self.workdir.mkdir(parents=True, exist_ok=True)

    def environment(self, profile: str | None = None) -> dict[str, str]:
        env = dict(os.environ)
        env.update({
            "HERMES_HOME": str(self.home),
            "NO_COLOR": "1",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        })
        if profile:
            env["HERMES_PROFILE"] = profile
            env["HERMES_CONFIG"] = str(self.profile_path(profile) / "config.yaml")
        return env

    def profile_path(self, profile: str) -> Path:
        return self.home / "profiles" / profile

    def command(self, arguments: list[str], *, profile: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(self.binary), *arguments],
            cwd=self.workdir,
            env=self.environment(profile),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            raise RuntimeError(f"Hermes command failed ({result.returncode}): {message}")
        return result

    def create_profile(self, name: str, *, clone_from: str | None = None) -> Path:
        target = self.profile_path(name)
        if target.exists():
            raise FileExistsError(f"profile already exists: {target}")
        arguments = ["profile", "create", name, "--no-alias"]
        if clone_from:
            arguments.extend(["--clone-all", "--clone-from", clone_from])
        else:
            arguments.append("--no-skills")
        self.command(arguments)
        if not target.is_dir():
            raise RuntimeError(f"Hermes did not create profile {name}")
        return target

    def ensure_profile(self, name: str, *, clone_from: str | None = None) -> Path:
        target = self.profile_path(name)
        if target.is_dir():
            return target
        return self.create_profile(name, clone_from=clone_from)

    def complete(self, profile: str, prompt: str, usage_path: Path) -> tuple[str, dict[str, Any]]:
        self.budget.take()
        usage_path.parent.mkdir(parents=True, exist_ok=True)
        result = self.command(
            [
                "-z", prompt,
                "--provider", self.provider,
                "--model", self.model,
                "--reasoning", REASONING,
                "--usage-file", str(usage_path.resolve()),
                "--in", str(self.workdir),
            ],
            profile=profile,
            timeout=360,
        )
        usage = json.loads(usage_path.read_text(encoding="utf-8")) if usage_path.is_file() else {}
        self.budget.record_usage(usage)
        return result.stdout.strip(), usage


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(value) + b"\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row in {path}")
        rows.append(value)
    return rows


def initialize_base(runner: HermesRunner) -> Path:
    profile = runner.profile_path("base")
    if profile.is_dir():
        required = (profile / "SOUL.md", profile / "memories" / "MEMORY.md", profile / "config.yaml")
        if not all(path.is_file() for path in required):
            raise RuntimeError(f"existing base profile is incomplete: {profile}")
        return profile
    profile = runner.create_profile("base")
    (profile / "SOUL.md").write_text(
        "# Delegated Procurement Agent\n\n"
        "Negotiate respectfully and seek sound agreements for the principal.\n",
        encoding="utf-8",
        newline="\n",
    )
    memory = profile / "memories" / "MEMORY.md"
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text(
        "# Persistent Practice Memory\n\n"
        "No domain-specific negotiation practice has been completed yet.\n",
        encoding="utf-8",
        newline="\n",
    )
    (profile / "config.yaml").write_text(
        f"model:\n  provider: {runner.provider}\n  default: {runner.model}\n"
        "platform_toolsets:\n  cli: []\n",
        encoding="utf-8",
        newline="\n",
    )
    return profile


def run_phase(
    runner: HermesRunner,
    profile: str,
    scenarios: list[Scenario],
    repetitions: int,
    output: Path,
    *,
    practice: bool,
    update_memory: bool,
) -> list[dict[str, Any]]:
    existing = read_jsonl(output)
    completed = {(str(row["scenario"]["id"]), int(row["repetition"])) for row in existing}
    rows = list(existing)
    for repetition in range(1, repetitions + 1):
        for scenario in scenarios:
            key = (scenario.id, repetition)
            if key in completed:
                continue
            usage_path = output.parent / "usage" / output.stem / f"{scenario.id}-r{repetition}.json"
            prompt = prompt_for(scenario, practice=practice)
            started = utc_now()
            raw, usage = runner.complete(profile, prompt, usage_path)
            decision = parse_decision(raw)
            score = evaluate_decision(scenario, decision)
            record = {
                "experiment": EXPERIMENT_ID,
                "phase": "practice" if practice else "evaluation",
                "started_at": started,
                "completed_at": utc_now(),
                "scenario": asdict(scenario),
                "repetition": repetition,
                "decision": asdict(decision),
                "score": asdict(score),
                "model": {"harness": "hermes", "provider": runner.provider, "model": runner.model, "reasoning": REASONING},
                "usage": usage,
                "raw_response": raw,
            }
            append_jsonl(output, record)
            rows.append(record)
            if update_memory:
                profile_root = runner.profile_path(profile)
                session_log = profile_root / "sessions" / "training-ground.jsonl"
                append_jsonl(session_log, record)
                memory = profile_root / "memories" / "MEMORY.md"
                with memory.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(
                        f"\n## {scenario.id}\n"
                        f"- Situation: seller asked {scenario.seller_ask}; private authority was {scenario.principal_max}; stance {scenario.stance}.\n"
                        f"- Action: {decision.action}; offer {decision.offer}.\n"
                        f"- World consequence: {score.consequence}\n"
                        f"- Agent reflection: {decision.reflection}\n"
                    )
            print(json.dumps({
                "event": "model_call",
                "phase": output.stem,
                "completed": len(rows),
                "phase_total": len(scenarios) * repetitions,
                "total_model_calls": runner.budget.used,
                "estimated_cost_usd": round(runner.budget.estimated_cost_usd, 8),
            }, sort_keys=True), flush=True)
            runner.budget.ensure_within_cost()
    return rows


def image_for(
    runner: HermesRunner,
    profile: str,
    output: Path,
    *,
    before_score: dict[str, Any],
    after_score: dict[str, Any] | None = None,
    development: dict[str, Any] | None = None,
    base_digest: str | None = None,
    evaluation_evidence: Path,
) -> str:
    if output.is_file():
        return load_image(output).manifest["image"]["digest"]
    cli = SubprocessHermesCLI(str(runner.binary), environment=runner.environment())
    export = HermesAdapter(cli).export(profile, "private", include_experience=True, include_workspace=True)
    evidence_digest = sha256_bytes(evaluation_evidence.read_bytes())
    evaluation: dict[str, Any] = {
        "id": "negotiation-held-out-v0.1",
        "status": "self_reported",
        "before": before_score,
        "evidence": {"kind": "evaluation", "path": evaluation_evidence.name, "digest": evidence_digest},
    }
    if after_score is not None:
        evaluation["after"] = after_score
    export.manifest["evaluations"] = [evaluation]
    if development is not None:
        export.manifest["development"] = development
    if base_digest is not None:
        export.manifest["lineage"] = {
            "base": {"uri": "before.aimg", "digest": base_digest},
            "fork_reason": "mission-specific contextual practice in a synthetic negotiation Training Ground",
        }
    publish_image(export, output)
    return load_image(output).manifest["image"]["digest"]


def prepare_run_root(path: Path, *, resume: bool = False) -> Path:
    resolved = path.resolve()
    if resolved.exists():
        if any(resolved.iterdir()) and not resume:
            raise FileExistsError(f"run root already exists and is not empty: {resolved}")
    else:
        resolved.mkdir(parents=True)
    return resolved


def probe(args: argparse.Namespace) -> int:
    root = prepare_run_root(Path(args.run_root))
    budget = CallBudget(1, args.max_cost_usd)
    runner = HermesRunner(Path(args.hermes), root / "hermes-home", root / "workspace", args.provider, args.model, budget)
    initialize_base(runner)
    scenario = generate_scenarios("probe", 1, EVALUATION_SEED)[0]
    rows = run_phase(runner, "base", [scenario], 1, root / "probe.jsonl", practice=False, update_memory=False)
    write_json(root / "probe-result.json", rows[0])
    print(json.dumps({
        "probe": "pass",
        "model_calls": budget.used,
        "estimated_cost_usd": round(budget.estimated_cost_usd, 8),
        "score": rows[0]["score"]["score"],
    }, sort_keys=True))
    return 0


def run_experiment(args: argparse.Namespace) -> int:
    root = prepare_run_root(Path(args.run_root), resume=args.resume)
    final_path = root / "final-evidence.json"
    if final_path.is_file():
        final = json.loads(final_path.read_text(encoding="utf-8"))
        print(json.dumps(final, sort_keys=True))
        return 0 if final["verdict"]["behavioral_claim_allowed"] else 2

    metadata_path = root / "run-metadata.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected_model = metadata["model"]
        actual_model = {"provider": args.provider, "model": args.model, "reasoning": REASONING}
        if expected_model != actual_model:
            raise RuntimeError(f"resume model mismatch: expected {expected_model}, received {actual_model}")
        started_at = str(metadata["started_at"])
    else:
        started_at = utc_now()
        metadata = {
            "experiment": EXPERIMENT_ID,
            "started_at": started_at,
            "harness": {"id": "hermes", "version": "0.20.5"},
            "model": {"provider": args.provider, "model": args.model, "reasoning": REASONING},
            "weights_changed": False,
            "synthetic_data_only": True,
            "model_call_budget": args.max_calls,
            "estimated_cost_budget_usd": args.max_cost_usd,
        }
        write_json(metadata_path, metadata)

    used, estimated_cost = prior_usage(root)
    budget = CallBudget(
        args.max_calls,
        args.max_cost_usd,
        used=used,
        estimated_cost_usd=estimated_cost,
    )
    runner = HermesRunner(Path(args.hermes), root / "hermes-home", root / "workspace", args.provider, args.model, budget)
    initialize_base(runner)
    training_scenarios = generate_scenarios("train", TRAINING_EPISODES, TRAINING_SEED)
    evaluation_scenarios = generate_scenarios("eval", EVALUATION_SCENARIOS, EVALUATION_SEED)
    if {item.id for item in training_scenarios} & {item.id for item in evaluation_scenarios}:
        raise RuntimeError("training and evaluation scenario ids overlap")

    write_json(root / "scenario-manifest.json", {
        "experiment": EXPERIMENT_ID,
        "training": [asdict(item) for item in training_scenarios],
        "evaluation": [asdict(item) for item in evaluation_scenarios],
    })
    runner.ensure_profile("beforeeval", clone_from="base")
    before_rows = run_phase(
        runner, "beforeeval", evaluation_scenarios, EVALUATION_REPETITIONS,
        root / "before-evaluation.jsonl", practice=False, update_memory=False,
    )
    before = aggregate(before_rows)
    write_json(root / "before-evaluation.json", before)
    before_digest = image_for(
        runner, "base", root / "before.aimg", before_score=before,
        evaluation_evidence=root / "before-evaluation.json", after_score=None,
    )

    runner.ensure_profile("training", clone_from="base")
    practice_metadata_path = root / "practice-metadata.json"
    if practice_metadata_path.is_file():
        practice_metadata = json.loads(practice_metadata_path.read_text(encoding="utf-8"))
    else:
        practice_metadata = {"started_at": utc_now(), "ended_at": None}
        write_json(practice_metadata_path, practice_metadata)
    practice_started = str(practice_metadata["started_at"])
    practice_rows = run_phase(
        runner, "training", training_scenarios, 1,
        root / "practice.jsonl", practice=True, update_memory=True,
    )
    if practice_metadata.get("ended_at") is None:
        practice_metadata["ended_at"] = utc_now()
        write_json(practice_metadata_path, practice_metadata)
    practice_ended = str(practice_metadata["ended_at"])
    runner.ensure_profile("aftereval", clone_from="training")
    after_rows = run_phase(
        runner, "aftereval", evaluation_scenarios, EVALUATION_REPETITIONS,
        root / "after-evaluation.jsonl", practice=False, update_memory=False,
    )
    after = aggregate(after_rows)
    write_json(root / "after-evaluation.json", after)

    practice_log = runner.profile_path("training") / "sessions" / "training-ground.jsonl"
    practice_duration = max(
        0,
        int(
            datetime.fromisoformat(practice_ended.replace("Z", "+00:00")).timestamp()
            - datetime.fromisoformat(practice_started.replace("Z", "+00:00")).timestamp()
        ),
    )
    development = {
        "method": "habitat",
        "started_at": practice_started,
        "ended_at": practice_ended,
        "duration_seconds": practice_duration,
        "episodes": len(practice_rows),
        "habitat": {"id": EXPERIMENT_ID, "version": HABITAT_VERSION},
        "notes": "Synthetic procurement practice; model weights unchanged; world consequences and agent reflections persisted between episodes.",
        "evidence": [{"kind": "session", "path": "sessions/training-ground.jsonl", "digest": sha256_bytes(practice_log.read_bytes())}],
    }
    trained_digest = image_for(
        runner, "training", root / "trained.aimg", before_score=before, after_score=after,
        development=development, base_digest=before_digest,
        evaluation_evidence=root / "after-evaluation.json",
    )

    if not runner.profile_path("restored").is_dir():
        adapter = HermesAdapter(SubprocessHermesCLI(str(runner.binary), environment=runner.environment()))
        adapter.native_restore(load_image(root / "trained.aimg"), "restored")
    restored_rows = run_phase(
        runner, "restored", evaluation_scenarios, EVALUATION_REPETITIONS,
        root / "restored-evaluation.jsonl", practice=False, update_memory=False,
    )
    restored = aggregate(restored_rows)
    write_json(root / "restored-evaluation.json", restored)
    verdict = analyze(before, after, restored)
    final = {
        "evidence_version": "agent-image-trained-agent-evidence/v0.1",
        "experiment": EXPERIMENT_ID,
        "started_at": started_at,
        "completed_at": utc_now(),
        "harness": {"id": "hermes", "version": "0.20.5"},
        "model": {"provider": args.provider, "model": args.model, "reasoning": REASONING},
        "weights_changed": False,
        "live_session_reused_after_restore": False,
        "episodes": len(practice_rows),
        "before": before,
        "after": after,
        "restored": restored,
        "verdict": verdict,
        "images": {"before": before_digest, "trained": trained_digest},
        "model_calls": budget.used,
        "estimated_cost_usd": round(budget.estimated_cost_usd, 8),
        "claim": "portable learned behavior demonstrated" if verdict["behavioral_claim_allowed"] else "behavioral portability not demonstrated",
    }
    write_json(root / "final-evidence.json", final)
    print(json.dumps(final, sort_keys=True))
    return 0 if verdict["behavioral_claim_allowed"] else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Run the preregistered Agent Image negotiation Training Ground.")
    subcommands = root.add_subparsers(dest="command", required=True)
    for name in ("probe", "run"):
        command = subcommands.add_parser(name)
        command.add_argument("--hermes", required=True)
        command.add_argument("--run-root", required=True)
        command.add_argument("--provider", default=MODEL_PROVIDER)
        command.add_argument("--model", default=MODEL_ID)
        command.add_argument("--max-cost-usd", type=float, default=MAX_ESTIMATED_COST_USD)
        if name == "run":
            command.add_argument("--max-calls", type=int, default=EXPECTED_MODEL_CALLS)
            command.add_argument("--resume", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "probe":
        return probe(args)
    return run_experiment(args)


if __name__ == "__main__":
    raise SystemExit(main())
