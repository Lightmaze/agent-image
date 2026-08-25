from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

from agent_image.adapters.hermes import HermesAdapter, SubprocessHermesCLI
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.errors import AgentImageError
from agent_image.image_archive import layer_root_digest, load_image, publish_image
from experiments.situated_negotiation_ground.domain import (
    BOOTSTRAP_SAMPLES,
    BOOTSTRAP_SEED,
    COHORT_POLICIES,
    EVALUATION_ORDER_SEED,
    EVALUATION_SCENARIOS,
    EVALUATION_SEED,
    EXPERIMENT_ID,
    PILOT_POLICIES,
    PILOT_SHUFFLED_POLICIES,
    POST_REPETITIONS,
    PRE_REPETITIONS,
    SHUFFLED_POLICIES,
    TRAINING_BLOCK_SIZE,
    TRAINING_EPISODES,
    TRAINING_SEED,
    aggregate,
    analyze_gate,
    bootstrap_paired_difference,
    consolidation_prompt,
    decision_prompt,
    evaluate_decision,
    feedback_prompt,
    generate_scenarios,
    invalid_response_score,
    parse_decision,
    parse_playbook,
    parse_reflection,
    render_playbook_memory,
    static_handbook,
)


REASONING = "none"
HERMES_VERSION = "0.20.5"
DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-v4-flash"
FORMAL_MAXIMUM_API_CALLS = 2_000
FORMAL_MAXIMUM_TOTAL_TOKENS = 90_000_000
FORMAL_MAXIMUM_COST_USD = 25.0
PILOT_MAXIMUM_API_CALLS = 160
PILOT_MAXIMUM_TOTAL_TOKENS = 5_000_000
PILOT_MAXIMUM_COST_USD = 5.0


@dataclass(frozen=True)
class ExperimentConfig:
    mode: str
    training_episodes: int
    block_size: int
    evaluation_scenarios: int
    pre_repetitions: int
    post_repetitions: int
    policies: Mapping[str, float]
    shuffled_policies: Mapping[str, float]
    training_seed: int
    evaluation_seed: int
    maximum_api_calls: int
    maximum_total_tokens: int
    maximum_cost_usd: float

    @property
    def expected_model_invocations(self) -> int:
        training_calls = 2 * (
            (2 * self.training_episodes)
            + (self.training_episodes // self.block_size)
        )
        evaluations = self.evaluation_scenarios * (
            self.pre_repetitions + (5 * self.post_repetitions)
        )
        return training_calls + evaluations


def formal_config() -> ExperimentConfig:
    return ExperimentConfig(
        mode="formal",
        training_episodes=TRAINING_EPISODES,
        block_size=TRAINING_BLOCK_SIZE,
        evaluation_scenarios=EVALUATION_SCENARIOS,
        pre_repetitions=PRE_REPETITIONS,
        post_repetitions=POST_REPETITIONS,
        policies=COHORT_POLICIES,
        shuffled_policies=SHUFFLED_POLICIES,
        training_seed=TRAINING_SEED,
        evaluation_seed=EVALUATION_SEED,
        maximum_api_calls=FORMAL_MAXIMUM_API_CALLS,
        maximum_total_tokens=FORMAL_MAXIMUM_TOTAL_TOKENS,
        maximum_cost_usd=FORMAL_MAXIMUM_COST_USD,
    )


def pilot_config() -> ExperimentConfig:
    return ExperimentConfig(
        mode="pilot",
        training_episodes=16,
        block_size=8,
        evaluation_scenarios=8,
        pre_repetitions=1,
        post_repetitions=1,
        policies=PILOT_POLICIES,
        shuffled_policies=PILOT_SHUFFLED_POLICIES,
        training_seed=TRAINING_SEED + 101,
        evaluation_seed=EVALUATION_SEED + 101,
        maximum_api_calls=PILOT_MAXIMUM_API_CALLS,
        maximum_total_tokens=PILOT_MAXIMUM_TOTAL_TOKENS,
        maximum_cost_usd=PILOT_MAXIMUM_COST_USD,
    )


class TokenBudget:
    def __init__(
        self,
        *,
        maximum_api_calls: int,
        maximum_total_tokens: int,
        maximum_cost_usd: float,
    ) -> None:
        self.maximum_api_calls = maximum_api_calls
        self.maximum_total_tokens = maximum_total_tokens
        self.maximum_cost_usd = maximum_cost_usd
        self.api_calls = 0
        self.total_tokens = 0
        self.estimated_cost_usd = 0.0

    def record(self, usage: Mapping[str, Any]) -> None:
        api_calls = self.api_calls + int(usage.get("api_calls", 0) or 0)
        total_tokens = self.total_tokens + int(usage.get("total_tokens", 0) or 0)
        estimated_cost = self.estimated_cost_usd + float(usage.get("estimated_cost_usd", 0.0) or 0.0)
        exceeded: dict[str, Any] = {}
        if api_calls > self.maximum_api_calls:
            exceeded["api_calls"] = {"observed": api_calls, "maximum": self.maximum_api_calls}
        if total_tokens > self.maximum_total_tokens:
            exceeded["total_tokens"] = {"observed": total_tokens, "maximum": self.maximum_total_tokens}
        if estimated_cost > self.maximum_cost_usd:
            exceeded["estimated_cost_usd"] = {
                "observed": estimated_cost,
                "maximum": self.maximum_cost_usd,
            }
        if exceeded:
            raise AgentImageError(
                "E_EXPERIMENT_BUDGET_EXCEEDED",
                "The persisted provider usage exceeds the experiment's fail-closed budget.",
                details=exceeded,
            )
        self.api_calls = api_calls
        self.total_tokens = total_tokens
        self.estimated_cost_usd = estimated_cost

    def as_dict(self) -> dict[str, Any]:
        return {
            "api_calls": self.api_calls,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 8),
            "limits": {
                "maximum_api_calls": self.maximum_api_calls,
                "maximum_total_tokens": self.maximum_total_tokens,
                "maximum_cost_usd": self.maximum_cost_usd,
            },
        }


def hermes_arguments(
    *,
    prompt: str,
    provider: str,
    model: str,
    usage_path: Path,
    workdir: Path,
    resume_session: str | None = None,
    profile: str | None = None,
) -> list[str]:
    arguments = [
        "-z",
        prompt,
        "--provider",
        provider,
        "--model",
        model,
        "--reasoning",
        REASONING,
        "--usage-file",
        str(usage_path.resolve()),
        "--in",
        str(workdir.resolve()),
        "--no-restore-cwd",
    ]
    if resume_session:
        arguments.extend(["--resume", resume_session])
    if profile:
        arguments.extend(["--profile", profile])
    return arguments


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(value) + b"\n")


def write_jsonl(path: Path, values: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join(canonical_json_bytes(dict(value)) + b"\n" for value in values)
    path.write_bytes(data)


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


def file_digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def directory_digest(root: Path, *, excluded: Iterable[str] = ()) -> str:
    exclusions = set(excluded)
    entries: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in exclusions:
            continue
        entries.append({"path": relative, "digest": file_digest(path)})
    return sha256_bytes(canonical_json_bytes(entries))


def load_existing_budget(root: Path, config: ExperimentConfig) -> TokenBudget:
    budget = TokenBudget(
        maximum_api_calls=config.maximum_api_calls,
        maximum_total_tokens=config.maximum_total_tokens,
        maximum_cost_usd=config.maximum_cost_usd,
    )
    for path in sorted((root / "usage").rglob("*.json")) if (root / "usage").is_dir() else []:
        usage = json.loads(path.read_text(encoding="utf-8"))
        budget.record(usage)
    return budget


class HermesRunner:
    def __init__(
        self,
        *,
        binary: Path,
        root: Path,
        provider: str,
        model: str,
        budget: TokenBudget,
    ) -> None:
        self.binary = binary.resolve()
        self.root = root.resolve()
        self.home = self.root / "hermes-home"
        self.workdir = self.root / "workspace"
        self.provider = provider
        self.model = model
        self.budget = budget
        self.home.mkdir(parents=True, exist_ok=True)
        self.workdir.mkdir(parents=True, exist_ok=True)

    def profile_path(self, profile: str) -> Path:
        return self.home / "profiles" / profile

    def environment(self, profile: str | None = None) -> dict[str, str]:
        environment = dict(os.environ)
        environment.update(
            {
                "HERMES_HOME": str(self.home),
                "NO_COLOR": "1",
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        if profile:
            environment["HERMES_PROFILE"] = profile
            environment["HERMES_CONFIG"] = str(self.profile_path(profile) / "config.yaml")
        return environment

    def command(
        self,
        arguments: Sequence[str],
        *,
        profile: str | None = None,
        timeout: int = 420,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
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

    def require_version(self) -> None:
        result = self.command(["--version"], timeout=30)
        if result.returncode != 0 or HERMES_VERSION not in result.stdout:
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                f"The experiment requires Hermes {HERMES_VERSION}.",
                details={"stdout": result.stdout.strip(), "stderr": result.stderr.strip()},
            )

    def create_profile(self, name: str, *, clone_from: str | None = None) -> Path:
        target = self.profile_path(name)
        if target.exists():
            raise AgentImageError("E_TARGET_EXISTS", f"Hermes profile already exists: {name}")
        arguments = ["profile", "create", name, "--no-alias"]
        if clone_from:
            arguments.extend(["--clone-all", "--clone-from", clone_from])
        else:
            arguments.append("--no-skills")
        result = self.command(arguments, timeout=120)
        if result.returncode != 0 or not target.is_dir():
            raise RuntimeError(
                f"Hermes profile creation failed for {name}: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return target

    def ensure_profile(self, name: str, *, clone_from: str | None = None) -> Path:
        target = self.profile_path(name)
        if target.is_dir():
            return target
        return self.create_profile(name, clone_from=clone_from)

    def complete(
        self,
        *,
        profile: str,
        prompt: str,
        call_id: str,
        resume_session: str | None = None,
    ) -> tuple[str, dict[str, Any], bool]:
        usage_path = self.root / "usage" / f"{call_id}.json"
        response_path = self.root / "responses" / f"{call_id}.txt"
        if usage_path.is_file():
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
            if not usage.get("completed") or usage.get("failed"):
                raise RuntimeError(f"provider call previously failed; no scientific resampling is allowed: {call_id}")
            if not response_path.is_file():
                raise RuntimeError(f"completed provider call has no persisted response: {call_id}")
            return response_path.read_text(encoding="utf-8").strip(), usage, True

        usage_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.parent.mkdir(parents=True, exist_ok=True)
        result = self.command(
            hermes_arguments(
                prompt=prompt,
                provider=self.provider,
                model=self.model,
                usage_path=usage_path,
                workdir=self.workdir,
                resume_session=resume_session,
                profile=profile,
            ),
            profile=profile,
        )
        if not usage_path.is_file():
            raise RuntimeError(
                f"Hermes produced no usage ledger for {call_id}: "
                f"exit={result.returncode}; output={(result.stderr or result.stdout).strip()}"
            )
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
        self.budget.record(usage)
        if usage.get("provider") != self.provider or usage.get("model") != self.model:
            raise RuntimeError(
                f"provider/model drift in {call_id}: "
                f"{usage.get('provider')}/{usage.get('model')}"
            )
        if result.returncode != 0 or not usage.get("completed") or usage.get("failed"):
            raise RuntimeError(
                f"Hermes model call failed for {call_id}: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        response_path.write_text(result.stdout.strip() + "\n", encoding="utf-8", newline="\n")
        return result.stdout.strip(), usage, False

    def verify_profile_surface(self, profile: str, *, require_memory: bool = True) -> dict[str, Any]:
        result = self.command(
            ["--profile", profile, "prompt-size", "--json"],
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Hermes prompt-surface inspection failed for {profile}: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        value = json.loads(result.stdout)
        memory_chars = int(value.get("memory", {}).get("chars", 0) or 0)
        tools_count = int(value.get("tools", {}).get("count", -1))
        if require_memory and memory_chars <= 0:
            raise RuntimeError(f"Hermes active profile {profile} did not load its MEMORY.md")
        if tools_count != 0:
            raise RuntimeError(f"Hermes active profile {profile} unexpectedly exposes {tools_count} tools")
        return {
            "profile": profile,
            "model": value.get("model"),
            "memory_chars": memory_chars,
            "memory_bytes": int(value.get("memory", {}).get("bytes", 0) or 0),
            "tools_count": tools_count,
        }

    def emit_progress(self, *, phase: str, completed: int, total: int, recovered: bool) -> None:
        print(
            json.dumps(
                {
                    "event": "recovered_model_call" if recovered else "model_call",
                    "phase": phase,
                    "completed": completed,
                    "phase_total": total,
                    "budget": self.budget.as_dict(),
                },
                sort_keys=True,
            ),
            flush=True,
        )


def initialize_profiles(runner: HermesRunner) -> None:
    base = runner.ensure_profile("base")
    soul = base / "SOUL.md"
    soul.write_text(
        "# Delegated Procurement Agent\n\n"
        "Protect the principal's interests, respect private authority, and return only the requested JSON.\n",
        encoding="utf-8",
        newline="\n",
    )
    memory = base / "memories" / "MEMORY.md"
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text(
        "# Persistent Practice Memory\n\n"
        "No cohort-specific situated negotiation practice has been completed.\n",
        encoding="utf-8",
        newline="\n",
    )
    (base / ".no-bundled-skills").write_text("\n", encoding="utf-8", newline="\n")
    (base / "config.yaml").write_text(
        f"model:\n  provider: {runner.provider}\n  default: {runner.model}\n"
        "agent:\n  reasoning_effort: none\n"
        "platform_toolsets:\n  cli: []\n",
        encoding="utf-8",
        newline="\n",
    )
    for name in ("handbook", "trained", "shuffled"):
        runner.ensure_profile(name, clone_from="base")
    handbook_memory = runner.profile_path("handbook") / "memories" / "MEMORY.md"
    if "Generic Negotiation Handbook" not in handbook_memory.read_text(encoding="utf-8"):
        handbook_memory.write_text(static_handbook(), encoding="utf-8", newline="\n")


def _response_reference(runner: HermesRunner, call_id: str, raw: str) -> dict[str, Any]:
    return {
        "path": (Path("responses") / f"{call_id}.txt").as_posix(),
        "digest": sha256_bytes((raw.strip() + "\n").encode("utf-8")),
        "privacy": "private",
    }


def _model_record(runner: HermesRunner) -> dict[str, Any]:
    return {
        "harness": "hermes",
        "harness_version": HERMES_VERSION,
        "provider": runner.provider,
        "model": runner.model,
        "reasoning": REASONING,
        "tools": [],
    }


def reflection_evidence(raw: str, expected_cohort: str) -> tuple[dict[str, Any], str | None]:
    try:
        value = parse_reflection(raw, expected_cohort)
    except (ValueError, json.JSONDecodeError) as error:
        return (
            {
                "valid": False,
                "expected_cohort": expected_cohort,
                "raw_response_digest": sha256_bytes((raw.strip() + "\n").encode("utf-8")),
            },
            f"{type(error).__name__}: {error}",
        )
    value["valid"] = True
    return value, None


def evaluate_arm(
    runner: HermesRunner,
    *,
    arm: str,
    profile: str,
    scenarios: Sequence[Any],
    repetitions: int,
    policies: Mapping[str, float],
    phase: str,
) -> list[dict[str, Any]]:
    output = runner.root / "evidence" / "evaluations" / f"{phase}-{arm}.jsonl"
    rows = read_jsonl(output)
    completed = {
        (str(row["scenario"]["id"]), int(row["repetition"]))
        for row in rows
    }
    total = len(scenarios) * repetitions
    order = [(repetition, scenario) for repetition in range(1, repetitions + 1) for scenario in scenarios]
    if phase == "post":
        random.Random(EVALUATION_ORDER_SEED + sum(ord(char) for char in arm)).shuffle(order)
    for repetition, scenario in order:
        key = (scenario.id, repetition)
        if key in completed:
            continue
        call_id = f"evaluation/{phase}/{arm}/{scenario.id}-r{repetition}"
        raw, usage, recovered = runner.complete(
            profile=profile,
            prompt=decision_prompt(scenario),
            call_id=call_id,
        )
        parse_error: str | None = None
        try:
            decision = parse_decision(raw)
            score = evaluate_decision(scenario, decision, policies)
        except (ValueError, json.JSONDecodeError) as error:
            decision = None
            score = invalid_response_score(scenario, policies)
            parse_error = f"{type(error).__name__}: {error}"
        row = {
            "experiment": EXPERIMENT_ID,
            "mode": phase,
            "arm": arm,
            "scenario": asdict(scenario),
            "repetition": repetition,
            "decision": asdict(decision) if decision is not None else None,
            "score": asdict(score),
            "model": _model_record(runner),
            "usage": usage,
            "response": _response_reference(runner, call_id, raw),
            "parse_error": parse_error,
            "recovered": recovered,
            "completed_at": utc_now(),
        }
        append_jsonl(output, row)
        rows.append(row)
        completed.add(key)
        runner.emit_progress(
            phase=f"{phase}-{arm}",
            completed=len(rows),
            total=total,
            recovered=recovered,
        )
    return rows


def _training_record_index(rows: Sequence[Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    return {int(row["episode"]): row for row in rows}


def train_arm(
    runner: HermesRunner,
    *,
    arm: str,
    profile: str,
    scenarios: Sequence[Any],
    policies: Mapping[str, float],
    block_size: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output = runner.root / "evidence" / "development" / f"{arm}.jsonl"
    consolidation_output = runner.root / "evidence" / "development" / f"{arm}-consolidations.jsonl"
    rows = read_jsonl(output)
    consolidations = read_jsonl(consolidation_output)
    completed = _training_record_index(rows)
    completed_blocks = {int(row["block"]): row for row in consolidations}
    playbook: dict[str, Any] | None = None
    if consolidations:
        playbook = dict(consolidations[-1]["playbook"])

    total_calls = (2 * len(scenarios)) + (len(scenarios) // block_size)
    accounted_calls = (2 * len(rows)) + len(consolidations)
    for block_start in range(0, len(scenarios), block_size):
        block_number = (block_start // block_size) + 1
        block_scenarios = scenarios[block_start : block_start + block_size]
        block_rows: list[dict[str, Any]] = []
        resume_session: str | None = None
        for episode_offset, scenario in enumerate(block_scenarios, start=1):
            episode = block_start + episode_offset
            existing = completed.get(episode)
            if existing is not None:
                block_rows.append(dict(existing))
                resume_session = str(existing["reflection_usage"]["session_id"])
                continue

            action_call_id = f"development/{arm}/episode-{episode:03d}-action"
            raw_action, action_usage, recovered_action = runner.complete(
                profile=profile,
                prompt=decision_prompt(scenario),
                call_id=action_call_id,
                resume_session=resume_session,
            )
            parse_error: str | None = None
            try:
                decision = parse_decision(raw_action)
                score = evaluate_decision(scenario, decision, policies)
            except (ValueError, json.JSONDecodeError) as error:
                decision = None
                score = invalid_response_score(scenario, policies)
                parse_error = f"{type(error).__name__}: {error}"

            action_session = action_usage.get("session_id")
            if not isinstance(action_session, str) or not action_session:
                raise RuntimeError(f"Hermes did not report an exact action session id for episode {episode}")
            feedback_call_id = f"development/{arm}/episode-{episode:03d}-reflection"
            raw_reflection, reflection_usage, recovered_reflection = runner.complete(
                profile=profile,
                prompt=feedback_prompt(scenario, decision, score),
                call_id=feedback_call_id,
                resume_session=action_session,
            )
            reflection, reflection_parse_error = reflection_evidence(raw_reflection, scenario.cohort)
            reflection_session = reflection_usage.get("session_id")
            if not isinstance(reflection_session, str) or not reflection_session:
                raise RuntimeError(f"Hermes did not report an exact reflection session id for episode {episode}")
            resume_session = reflection_session
            row = {
                "experiment": EXPERIMENT_ID,
                "arm": arm,
                "episode": episode,
                "block": block_number,
                "scenario": asdict(scenario),
                "decision": asdict(decision) if decision is not None else None,
                "score": asdict(score),
                "reflection": reflection,
                "model": _model_record(runner),
                "action_usage": action_usage,
                "reflection_usage": reflection_usage,
                "action_response": _response_reference(runner, action_call_id, raw_action),
                "reflection_response": _response_reference(runner, feedback_call_id, raw_reflection),
                "parse_error": parse_error,
                "reflection_parse_error": reflection_parse_error,
                "recovered": recovered_action or recovered_reflection,
                "completed_at": utc_now(),
            }
            append_jsonl(output, row)
            append_jsonl(
                runner.profile_path(profile) / "sessions" / "situated-training-ground.jsonl",
                row,
            )
            rows.append(row)
            completed[episode] = row
            block_rows.append(row)
            accounted_calls += 2
            runner.emit_progress(
                phase=f"development-{arm}",
                completed=accounted_calls,
                total=total_calls,
                recovered=recovered_action or recovered_reflection,
            )

        existing_consolidation = completed_blocks.get(block_number)
        if existing_consolidation is not None:
            playbook = dict(existing_consolidation["playbook"])
            continue
        if resume_session is None:
            raise RuntimeError(f"block {block_number} has no session lineage for consolidation")
        consolidation_call_id = f"development/{arm}/block-{block_number:02d}-consolidation"
        raw_playbook, consolidation_usage, recovered = runner.complete(
            profile=profile,
            prompt=consolidation_prompt(block_rows, playbook, policies),
            call_id=consolidation_call_id,
            resume_session=resume_session,
        )
        playbook = parse_playbook(raw_playbook, policies)
        evidence_digest = sha256_bytes(canonical_json_bytes(block_rows))
        memory_text = render_playbook_memory(
            playbook,
            arm=arm,
            completed_episodes=block_start + len(block_rows),
            evidence_digest=evidence_digest,
        )
        memory_path = runner.profile_path(profile) / "memories" / "MEMORY.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text(memory_text, encoding="utf-8", newline="\n")
        consolidation = {
            "experiment": EXPERIMENT_ID,
            "arm": arm,
            "block": block_number,
            "episodes": [int(row["episode"]) for row in block_rows],
            "playbook": playbook,
            "usage": consolidation_usage,
            "response": _response_reference(runner, consolidation_call_id, raw_playbook),
            "source_evidence_digest": evidence_digest,
            "memory_digest": file_digest(memory_path),
            "recovered": recovered,
            "completed_at": utc_now(),
        }
        append_jsonl(consolidation_output, consolidation)
        append_jsonl(
            runner.profile_path(profile) / "sessions" / "situated-consolidations.jsonl",
            consolidation,
        )
        consolidations.append(consolidation)
        completed_blocks[block_number] = consolidation
        accounted_calls += 1
        runner.emit_progress(
            phase=f"development-{arm}",
            completed=accounted_calls,
            total=total_calls,
            recovered=recovered,
        )

    if playbook is None:
        raise RuntimeError(f"development arm {arm} produced no consolidated playbook")
    # The profile copies are materialized from the authoritative external
    # ledgers so an interruption between two appends cannot create a partial
    # or duplicate history inside the checkpointed Agent state.
    write_jsonl(
        runner.profile_path(profile) / "sessions" / "situated-training-ground.jsonl",
        rows,
    )
    write_jsonl(
        runner.profile_path(profile) / "sessions" / "situated-consolidations.jsonl",
        consolidations,
    )
    return rows, playbook


def _evidence_index(paths: Sequence[Path], root: Path) -> bytes:
    value = {
        "experiment": EXPERIMENT_ID,
        "privacy": "private",
        "entries": [
            {
                "path": path.relative_to(root).as_posix(),
                "digest": file_digest(path),
                "size": path.stat().st_size,
            }
            for path in sorted(paths)
        ],
    }
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def build_checkpoint(
    runner: HermesRunner,
    *,
    profile: str,
    output: Path,
    evaluation_paths: Sequence[Path],
    development_paths: Sequence[Path] = (),
    before_summary: Mapping[str, Any],
    parent_digest: str | None = None,
) -> str:
    if output.is_file():
        return str(load_image(output).manifest["image"]["digest"])
    cli = SubprocessHermesCLI(
        str(runner.binary),
        environment=runner.environment(),
        timeout_seconds=180,
    )
    exported = HermesAdapter(cli).export(
        profile,
        "private",
        include_experience=True,
        include_workspace=True,
    )
    if evaluation_paths:
        payload = _evidence_index(evaluation_paths, runner.root)
        path = "layers/evaluation/situated-evidence-index.json"
        exported.payloads[path] = payload
        exported.manifest["layers"].append(
            {
                "id": "situated-evaluation-evidence-index",
                "kind": "evaluation",
                "media_type": "application/vnd.agentimage.evidence-index.v0.1+json",
                "path": path,
                "digest": sha256_bytes(payload),
                "size": len(payload),
                "privacy": "private",
                "portability": "portable",
                "source": {
                    "origin": EXPERIMENT_ID,
                    "reason": "digest-preserving references to private held-out evaluation evidence",
                },
            }
        )
    if development_paths:
        payload = _evidence_index(development_paths, runner.root)
        path = "layers/development/situated-development-index.json"
        exported.payloads[path] = payload
        exported.manifest["layers"].append(
            {
                "id": "situated-development-evidence-index",
                "kind": "development",
                "media_type": "application/vnd.agentimage.evidence-index.v0.1+json",
                "path": path,
                "digest": sha256_bytes(payload),
                "size": len(payload),
                "privacy": "private",
                "portability": "portable",
                "source": {
                    "origin": EXPERIMENT_ID,
                    "reason": "digest-preserving references to private causal practice evidence",
                },
            }
        )
        exported.manifest["development"] = {
            "method": "habitat",
            "environment": "situated-negotiation-training-ground-v0.2",
            "episodes": len(read_jsonl(development_paths[0])),
            "weights_changed": False,
            "evidence": {
                "path": "layers/development/situated-development-index.json",
                "digest": sha256_bytes(payload),
                "status": "self_reported",
            },
        }
    exported.manifest["evaluations"] = [
        {
            "id": "situated-negotiation-held-out-v0.2-before",
            "status": "self_reported",
            "score": dict(before_summary),
            "evidence": {
                "path": "layers/evaluation/situated-evidence-index.json",
                "privacy": "private",
            },
        }
    ]
    exported.manifest.setdefault("runtime", {})["model"] = {
        "provider": runner.provider,
        "id": runner.model,
    }
    if parent_digest:
        exported.manifest["lineage"] = {
            "parents": [{"digest": parent_digest, "relationship": "developed_from"}],
            "fork_reason": "mission-specific causal practice in a synthetic Training Ground",
        }
    exported.manifest["image"]["digest"] = layer_root_digest(exported.manifest["layers"])
    publish_image(exported, output)
    return str(load_image(output).manifest["image"]["digest"])


def restore_checkpoint(runner: HermesRunner, image: Path, target: str = "restored") -> dict[str, Any]:
    target_path = runner.profile_path(target)
    adapter = HermesAdapter(
        SubprocessHermesCLI(
            str(runner.binary),
            environment=runner.environment(),
            timeout_seconds=180,
        )
    )
    if target_path.is_dir():
        return {
            "operation": "restore",
            "target": target,
            "validated": True,
            "recovered_existing_target": True,
        }
    return adapter.native_restore(load_image(image), target)


def evaluate_post_interleaved(
    runner: HermesRunner,
    *,
    arms: Mapping[str, str],
    scenarios: Sequence[Any],
    repetitions: int,
    policies: Mapping[str, float],
) -> dict[str, list[dict[str, Any]]]:
    outputs = {
        arm: runner.root / "evidence" / "evaluations" / f"post-{arm}.jsonl"
        for arm in arms
    }
    rows = {arm: read_jsonl(path) for arm, path in outputs.items()}
    completed = {
        arm: {
            (str(row["scenario"]["id"]), int(row["repetition"]))
            for row in arm_rows
        }
        for arm, arm_rows in rows.items()
    }
    schedule = [
        (arm, repetition, scenario)
        for repetition in range(1, repetitions + 1)
        for scenario in scenarios
        for arm in arms
    ]
    random.Random(EVALUATION_ORDER_SEED).shuffle(schedule)
    total = len(schedule)
    total_completed = sum(len(arm_rows) for arm_rows in rows.values())
    for arm, repetition, scenario in schedule:
        key = (scenario.id, repetition)
        if key in completed[arm]:
            continue
        call_id = f"evaluation/post/{arm}/{scenario.id}-r{repetition}"
        raw, usage, recovered = runner.complete(
            profile=arms[arm],
            prompt=decision_prompt(scenario),
            call_id=call_id,
        )
        parse_error: str | None = None
        try:
            decision = parse_decision(raw)
            score = evaluate_decision(scenario, decision, policies)
        except (ValueError, json.JSONDecodeError) as error:
            decision = None
            score = invalid_response_score(scenario, policies)
            parse_error = f"{type(error).__name__}: {error}"
        row = {
            "experiment": EXPERIMENT_ID,
            "mode": "post",
            "arm": arm,
            "scenario": asdict(scenario),
            "repetition": repetition,
            "decision": asdict(decision) if decision is not None else None,
            "score": asdict(score),
            "model": _model_record(runner),
            "usage": usage,
            "response": _response_reference(runner, call_id, raw),
            "parse_error": parse_error,
            "recovered": recovered,
            "completed_at": utc_now(),
        }
        append_jsonl(outputs[arm], row)
        rows[arm].append(row)
        completed[arm].add(key)
        total_completed += 1
        runner.emit_progress(
            phase=f"post-interleaved:{arm}",
            completed=total_completed,
            total=total,
            recovered=recovered,
        )
    return rows


def prepare_run_root(path: Path, *, resume: bool) -> Path:
    root = path.resolve()
    if root.exists() and any(root.iterdir()) and not resume:
        raise AgentImageError("E_TARGET_EXISTS", f"Run root is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _git_value(root: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments)} failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


def validate_registration(repository: Path, config: ExperimentConfig) -> dict[str, Any]:
    path = repository / "experiments" / "situated_negotiation_ground" / "preregistration.yaml"
    registration = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.mode == "formal":
        if registration.get("status") != "frozen_before_formal_run":
            raise RuntimeError("formal calls require a committed preregistration with status frozen_before_formal_run")
        if _git_value(repository, ["status", "--porcelain"]):
            raise RuntimeError("formal provider calls require a clean Git worktree")
        if int(registration["budget"]["expected_model_invocations"]) != config.expected_model_invocations:
            raise RuntimeError("formal invocation count no longer matches preregistration")
    elif registration.get("status") not in {"draft_pre_pilot", "frozen_before_formal_run"}:
        raise RuntimeError(f"unrecognized preregistration status: {registration.get('status')}")
    return {
        "path": path.relative_to(repository).as_posix(),
        "digest": file_digest(path),
        "status": registration["status"],
        "git_commit": _git_value(repository, ["rev-parse", "HEAD"]),
    }


def _write_human_report(path: Path, evidence: Mapping[str, Any]) -> None:
    summaries = evidence["evaluation"]["summaries"]
    lines = [
        f"# {EXPERIMENT_ID} — {evidence['mode']} result",
        "",
        f"Gate E: **{evidence['verdict']['gate_e']}**",
        f"Behavioral claim allowed: **{str(evidence['verdict']['behavioral_claim_allowed']).lower()}**",
        "",
        "## Arm scores",
        "",
        "| Arm | Score | Scenarios | Records | Leaks |",
        "|---|---:|---:|---:|---:|",
    ]
    for arm, summary in summaries.items():
        lines.append(
            f"| {arm} | {summary['score']:.6f} | {summary['scenarios']} | "
            f"{summary['records']} | {summary['reservation_price_leaks']} |"
        )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            evidence["claim"],
            "",
            "The seller world is synthetic and explicitly marked as a test fixture. "
            "This result is not evidence of real-world procurement performance or cross-harness P3 portability.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def execute_experiment(
    *,
    repository: Path,
    run_root: Path,
    binary: Path,
    provider: str,
    model: str,
    config: ExperimentConfig,
    resume: bool,
) -> int:
    root = prepare_run_root(run_root, resume=resume)
    final_path = root / "final-evidence.json"
    if final_path.is_file():
        evidence = json.loads(final_path.read_text(encoding="utf-8"))
        print(json.dumps(evidence["verdict"], sort_keys=True))
        if evidence["mode"] == "pilot":
            return 0
        return 0 if evidence["verdict"]["behavioral_claim_allowed"] else 2

    current_registration = validate_registration(repository, config)
    registration = current_registration
    metadata_path = root / "run-metadata.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected = {"provider": provider, "model": model, "reasoning": REASONING}
        if metadata["model"] != expected or metadata["mode"] != config.mode:
            raise RuntimeError("resume parameters do not match the persisted run metadata")
        registration = dict(metadata["preregistration"])
        if (
            registration.get("digest") != current_registration.get("digest")
            or registration.get("status") != current_registration.get("status")
        ):
            raise RuntimeError("the frozen preregistration changed after formal calls began")
    else:
        metadata = {
            "experiment": EXPERIMENT_ID,
            "mode": config.mode,
            "started_at": utc_now(),
            "preregistration": registration,
            "model": {"provider": provider, "model": model, "reasoning": REASONING},
            "harness": {"id": "hermes", "version": HERMES_VERSION},
            "weights_changed": False,
            "tools": [],
            "synthetic_data_only": True,
            "expected_model_invocations": config.expected_model_invocations,
            "budget": {
                "maximum_api_calls": config.maximum_api_calls,
                "maximum_total_tokens": config.maximum_total_tokens,
                "maximum_cost_usd": config.maximum_cost_usd,
            },
        }
        write_json(metadata_path, metadata)

    budget = load_existing_budget(root, config)
    runner = HermesRunner(
        binary=binary,
        root=root,
        provider=provider,
        model=model,
        budget=budget,
    )
    runner.require_version()
    initialize_profiles(runner)
    surface_checks: dict[str, Any] = {
        "base": runner.verify_profile_surface("base"),
        "handbook": runner.verify_profile_surface("handbook"),
    }
    training_scenarios = generate_scenarios(
        "train" if config.mode == "formal" else "pilot-train",
        config.training_episodes,
        config.training_seed,
        policies=config.policies,
    )
    evaluation_scenarios = generate_scenarios(
        "eval" if config.mode == "formal" else "pilot-eval",
        config.evaluation_scenarios,
        config.evaluation_seed,
        policies=config.policies,
    )
    if {item.id for item in training_scenarios} & {item.id for item in evaluation_scenarios}:
        raise RuntimeError("training and held-out scenario ids overlap")

    before_rows = evaluate_arm(
        runner,
        arm="before",
        profile="base",
        scenarios=evaluation_scenarios,
        repetitions=config.pre_repetitions,
        policies=config.policies,
        phase="pre",
    )
    before_summary = aggregate(before_rows)
    before_path = root / "evidence" / "evaluations" / "pre-before.jsonl"
    before_image = root / "artifacts" / "before.aimg"
    before_digest = build_checkpoint(
        runner,
        profile="base",
        output=before_image,
        evaluation_paths=[before_path],
        before_summary=before_summary,
    )

    trained_rows, trained_playbook = train_arm(
        runner,
        arm="trained",
        profile="trained",
        scenarios=training_scenarios,
        policies=config.policies,
        block_size=config.block_size,
    )
    shuffled_rows, shuffled_playbook = train_arm(
        runner,
        arm="shuffled",
        profile="shuffled",
        scenarios=training_scenarios,
        policies=config.shuffled_policies,
        block_size=config.block_size,
    )
    surface_checks["trained"] = runner.verify_profile_surface("trained")
    surface_checks["shuffled"] = runner.verify_profile_surface("shuffled")
    development_paths = [
        root / "evidence" / "development" / "trained.jsonl",
        root / "evidence" / "development" / "trained-consolidations.jsonl",
    ]
    trained_image = root / "artifacts" / "trained.aimg"
    trained_digest = build_checkpoint(
        runner,
        profile="trained",
        output=trained_image,
        evaluation_paths=[before_path],
        development_paths=development_paths,
        before_summary=before_summary,
        parent_digest=before_digest,
    )
    source_archive_before = file_digest(trained_image)
    restore_report = restore_checkpoint(runner, trained_image)
    surface_checks["restored"] = runner.verify_profile_surface("restored")
    source_archive_after_restore = file_digest(trained_image)
    if source_archive_before != source_archive_after_restore:
        raise RuntimeError("trained source image changed during native restore")

    post_rows = evaluate_post_interleaved(
        runner,
        arms={
            "concurrent_base": "base",
            "handbook": "handbook",
            "trained": "trained",
            "shuffled": "shuffled",
            "restored": "restored",
        },
        scenarios=evaluation_scenarios,
        repetitions=config.post_repetitions,
        policies=config.policies,
    )
    summaries = {"before": before_summary}
    summaries.update({arm: aggregate(rows) for arm, rows in post_rows.items()})
    interval = bootstrap_paired_difference(
        post_rows["trained"],
        post_rows["concurrent_base"],
        samples=BOOTSTRAP_SAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    measured_verdict = analyze_gate(
        before=summaries["before"],
        concurrent_base=summaries["concurrent_base"],
        handbook=summaries["handbook"],
        trained=summaries["trained"],
        shuffled=summaries["shuffled"],
        restored=summaries["restored"],
        paired_interval=interval,
    )
    if config.mode == "pilot":
        verdict = dict(measured_verdict)
        verdict["pilot_numeric_gate"] = measured_verdict["gate_e"]
        verdict["gate_e"] = "not_applicable_pilot"
        verdict["behavioral_claim_allowed"] = False
    else:
        verdict = measured_verdict

    trained_profile = runner.profile_path("trained")
    restored_profile = runner.profile_path("restored")
    preserved_state = {
        "memory": {
            "trained": file_digest(trained_profile / "memories" / "MEMORY.md"),
            "restored": file_digest(restored_profile / "memories" / "MEMORY.md"),
        },
        "practice_history": {
            "trained": file_digest(trained_profile / "sessions" / "situated-training-ground.jsonl"),
            "restored": file_digest(restored_profile / "sessions" / "situated-training-ground.jsonl"),
        },
        "consolidations": {
            "trained": file_digest(trained_profile / "sessions" / "situated-consolidations.jsonl"),
            "restored": file_digest(restored_profile / "sessions" / "situated-consolidations.jsonl"),
        },
    }
    preserved_state["all_equal"] = all(
        value["trained"] == value["restored"]
        for key, value in preserved_state.items()
        if key != "all_equal"
    )
    if not preserved_state["all_equal"]:
        raise RuntimeError("fresh native restore did not preserve the declared developed state")

    evidence = {
        "experiment": EXPERIMENT_ID,
        "mode": config.mode,
        "started_at": metadata["started_at"],
        "completed_at": utc_now(),
        "preregistration": registration,
        "infrastructure_amendments": [
            {
                "id": "AMENDMENT-001-WINDOWS-TRANSPORT",
                "path": "experiments/situated_negotiation_ground/AMENDMENT-001-WINDOWS-TRANSPORT.md",
                "digest": file_digest(
                    repository
                    / "experiments"
                    / "situated_negotiation_ground"
                    / "AMENDMENT-001-WINDOWS-TRANSPORT.md"
                ),
                "git_commit": _git_value(repository, ["rev-parse", "HEAD"]),
                "changed_samples_or_thresholds": False,
            }
        ],
        "model": metadata["model"],
        "harness": metadata["harness"],
        "harness_prompt_surfaces": surface_checks,
        "budget": budget.as_dict(),
        "world": {
            "mock_point": "MOCK-SITUATED-SELLER-WORLD-001",
            "synthetic": True,
            "training_scenarios": len(training_scenarios),
            "held_out_scenarios": len(evaluation_scenarios),
            "training_and_evaluation_ids_disjoint": True,
        },
        "development": {
            "trained_episodes": len(trained_rows),
            "shuffled_episodes": len(shuffled_rows),
            "trained_playbook": trained_playbook,
            "shuffled_playbook": shuffled_playbook,
            "raw_evidence_privacy": "private",
        },
        "artifacts": {
            "before": {"path": str(before_image), "image_digest": before_digest},
            "trained": {
                "path": str(trained_image),
                "image_digest": trained_digest,
                "archive_digest_before_restore": source_archive_before,
                "archive_digest_after_restore": source_archive_after_restore,
                "source_immutable": source_archive_before == source_archive_after_restore,
            },
            "restore_report": restore_report,
            "preserved_state": preserved_state,
        },
        "evaluation": {
            "summaries": summaries,
            "paired_bootstrap": interval,
            "schedule": "seeded_interleaving",
        },
        "verdict": verdict,
        "claim": (
            "Pilot data cannot authorize a behavioral claim."
            if config.mode == "pilot"
            else (
                "Mission-specific developed state was retained by a fresh native restore under the pinned same-harness contract."
                if verdict["behavioral_claim_allowed"]
                else "Behavioral portability was not demonstrated; negative evidence is retained without reinterpretation."
            )
        ),
    }
    write_json(final_path, evidence)
    _write_human_report(root / "final-evidence.md", evidence)
    print(json.dumps(verdict, sort_keys=True), flush=True)
    if config.mode == "pilot":
        return 0
    return 0 if verdict["behavioral_claim_allowed"] else 2


def build_parser(repository: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Situated Negotiation Training Ground v0.2")
    subparsers = parser.add_subparsers(dest="command", required=True)
    default_hermes = repository / ".venv-hermes" / "Scripts" / "hermes.exe"
    for command in ("pilot", "run"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--run-root", required=True)
        subparser.add_argument("--hermes", default=str(default_hermes))
        subparser.add_argument("--provider", default=DEFAULT_PROVIDER)
        subparser.add_argument("--model", default=DEFAULT_MODEL)
        subparser.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    repository = Path(__file__).resolve().parents[2]
    parser = build_parser(repository)
    args = parser.parse_args(argv)
    config = pilot_config() if args.command == "pilot" else formal_config()
    try:
        return execute_experiment(
            repository=repository,
            run_root=Path(args.run_root),
            binary=Path(args.hermes),
            provider=str(args.provider),
            model=str(args.model),
            config=config,
            resume=bool(args.resume),
        )
    except AgentImageError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, sort_keys=True), flush=True)
        return 1
    except Exception as error:
        print(
            json.dumps(
                {"error": {"code": "E_EXPERIMENT_FAILED", "message": f"{type(error).__name__}: {error}"}},
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
