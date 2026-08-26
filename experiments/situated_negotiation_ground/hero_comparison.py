from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from agent_image.adapters.hermes import HermesAdapter, SubprocessHermesCLI
from agent_image.errors import AgentImageError
from agent_image.image_archive import load_image
from experiments.situated_negotiation_ground.domain import (
    COHORT_POLICIES,
    aggregate,
    decision_prompt,
    evaluate_decision,
    generate_scenarios,
    invalid_response_score,
    parse_decision,
)
from experiments.situated_negotiation_ground.runner import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    HERMES_VERSION,
    HermesRunner,
    TokenBudget,
    _model_record,
    _response_reference,
    append_jsonl,
    file_digest,
    utc_now,
    write_json,
)


EXPERIMENT_ID = "agent-image-public-hero-comparison-v0.1"
ARM_PROFILES = {
    "fresh": "fresh",
    "public_restored": "public-restored",
}


def _git_value(repository: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or "git command failed")
    return result.stdout.strip()


def _require_clean_repository(repository: Path) -> str:
    dirty = _git_value(repository, ["status", "--porcelain", "--untracked-files=all"])
    if dirty:
        raise RuntimeError("provider calls require a clean repository with the frozen preregistration committed")
    return _git_value(repository, ["rev-parse", "HEAD"])


def _load_registration(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("hero preregistration must be a YAML object")
    if value.get("experiment") != EXPERIMENT_ID:
        raise RuntimeError("hero preregistration experiment id drifted")
    if value.get("status") != "frozen_before_provider_calls":
        raise RuntimeError("hero preregistration is not frozen before provider calls")
    held_out = int(value["evaluation"]["held_out_scenarios"])
    repetitions = int(value["evaluation"]["repetitions_per_scenario"])
    expected = held_out * repetitions * len(ARM_PROFILES)
    if expected != int(value["evaluation"]["total_model_invocations"]):
        raise RuntimeError("hero preregistration invocation count is internally inconsistent")
    if expected > int(value["budget"]["maximum_api_calls"]):
        raise RuntimeError("hero preregistration invocation count exceeds its budget")
    return value


def _require_pinned_image(path: Path, registration: Mapping[str, Any], key: str) -> dict[str, Any]:
    expected = registration["artifacts"][key]
    document = load_image(path)
    actual_image = str(document.manifest["image"]["digest"])
    if actual_image != str(expected["image_digest"]):
        raise RuntimeError(f"{key} image digest drifted: {actual_image}")
    if key == "public_image":
        actual_file = file_digest(path)
        if actual_file != str(expected["file_digest"]):
            raise RuntimeError(f"public image file digest drifted: {actual_file}")
    return {"document": document, "image_digest": actual_image, "file_digest": file_digest(path)}


def _restore_once(
    runner: HermesRunner,
    *,
    image: Any,
    target: str,
    report_path: Path,
) -> dict[str, Any]:
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not runner.profile_path(target).is_dir():
            raise RuntimeError(f"restore report exists but Hermes profile is missing: {target}")
        return report
    adapter = HermesAdapter(
        SubprocessHermesCLI(
            str(runner.binary),
            environment=runner.environment(),
        )
    )
    report = adapter.native_restore(image, target)
    write_json(report_path, report)
    return report


def _prepare_fresh_profile(runner: HermesRunner) -> Path:
    profile = runner.ensure_profile("fresh")
    (profile / "SOUL.md").write_text(
        "# Delegated Procurement Agent\n\n"
        "Protect the principal's interests, respect private authority, and return only the requested JSON.\n",
        encoding="utf-8",
        newline="\n",
    )
    memory = profile / "memories" / "MEMORY.md"
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text(
        "# Persistent Practice Memory\n\n"
        "No cohort-specific situated negotiation practice has been completed.\n",
        encoding="utf-8",
        newline="\n",
    )
    (profile / ".no-bundled-skills").write_text("\n", encoding="utf-8", newline="\n")
    (profile / "config.yaml").write_text(
        f"model:\n  provider: {runner.provider}\n  default: {runner.model}\n"
        "agent:\n  reasoning_effort: none\n"
        "platform_toolsets:\n  cli: []\n",
        encoding="utf-8",
        newline="\n",
    )
    return profile


def comparison_schedule(
    *,
    scenarios: Sequence[Any],
    repetitions: int,
    seed: int,
) -> list[dict[str, Any]]:
    schedule = [
        {"arm": arm, "scenario": scenario, "repetition": repetition}
        for arm in ARM_PROFILES
        for scenario in scenarios
        for repetition in range(1, repetitions + 1)
    ]
    random.Random(seed).shuffle(schedule)
    return schedule


def analyze_hero_result(
    summaries: Mapping[str, Mapping[str, Any]],
    *,
    thresholds: Mapping[str, Any],
    state_equal: bool,
) -> dict[str, Any]:
    fresh = float(summaries["fresh"]["score"])
    public = float(summaries["public_restored"]["score"])
    public_gain = public - fresh
    maximum_leaks = int(thresholds["maximum_reservation_price_leaks"])
    gates = {
        "public_restored_gain": public_gain >= float(thresholds["minimum_public_restored_minus_fresh"]),
        "reservation_price_leaks": all(
            int(summary["reservation_price_leaks"]) <= maximum_leaks for summary in summaries.values()
        ),
        "developed_state_equal": state_equal,
    }
    return {
        "scores": {key: float(value["score"]) for key, value in summaries.items()},
        "public_restored_gain": round(public_gain, 6),
        "gates": gates,
        "passed": all(gates.values()),
    }


def _state_comparison(runner: HermesRunner, image: Any, relative_paths: Sequence[str]) -> dict[str, Any]:
    semantic_layers = {
        str(layer.get("source", {}).get("path")): layer
        for layer in image.manifest["layers"]
        if isinstance(layer.get("source"), Mapping) and layer.get("source", {}).get("path")
    }
    values: dict[str, Any] = {}
    for relative in relative_paths:
        public_path = runner.profile_path(ARM_PROFILES["public_restored"]) / Path(relative)
        layer = semantic_layers.get(relative)
        if not public_path.is_file() or layer is None:
            raise RuntimeError(f"required developed-state file is missing after restore: {relative}")
        actual = file_digest(public_path)
        expected = str(layer["digest"])
        values[relative] = {
            "image_layer": expected,
            "public_restored": actual,
            "equal": actual == expected,
        }
    values["all_equal"] = all(item["equal"] for item in values.values())
    return values


def _write_public_markdown(path: Path, evidence: Mapping[str, Any]) -> None:
    summaries = evidence["evaluation"]["summaries"]
    verdict = evidence["verdict"]
    status = "PASS" if verdict["passed"] else "FAIL"
    lines = [
        "# Public hero image — fresh restore comparison",
        "",
        f"Result: **{status}**",
        "",
        "This bounded comparison asks one release question: does the public, freshly restored Agent retain the mission-specific capability of its private trained parent? It does not claim real-world procurement competence.",
        "",
        "| Arm | Mean score | Reservation-price leaks |",
        "|---|---:|---:|",
    ]
    for arm in ("fresh", "public_restored"):
        summary = summaries[arm]
        lines.append(f"| `{arm}` | {float(summary['score']):.6f} | {int(summary['reservation_price_leaks'])} |")
    lines.extend(
        [
            "",
            f"- Public-restored gain over fresh: `{float(verdict['public_restored_gain']):.6f}`",
            "",
            "The two arms used Hermes 0.20.5, DeepSeek `deepseek-v4-flash`, reasoning `none`, no tools, 12 new synthetic held-out scenarios, and two repetitions per scenario. The 48 calls were globally interleaved from a frozen seed.",
            "",
            "Raw model responses and credentials remain local and private. The public evidence contains aggregate scores, content digests, the frozen preregistration digest, and the release verdict.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def execute(
    *,
    repository: Path,
    run_root: Path,
    public_image: Path,
    preregistration_path: Path,
    public_json: Path,
    public_markdown: Path,
    binary: Path,
    provider: str,
    model: str,
    resume: bool,
    credential_env_file: Path | None,
) -> int:
    registration = _load_registration(preregistration_path)
    if provider != registration["model_policy"]["provider"] or model != registration["model_policy"]["model"]:
        raise RuntimeError("provider/model must match the frozen hero preregistration")
    if run_root.exists() and any(run_root.iterdir()) and not resume:
        raise AgentImageError("E_TARGET_EXISTS", f"Hero comparison run root already exists: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)

    commit = _require_clean_repository(repository)
    public = _require_pinned_image(public_image, registration, "public_image")
    source_before = file_digest(public_image)

    budget = TokenBudget(
        maximum_api_calls=int(registration["budget"]["maximum_api_calls"]),
        maximum_total_tokens=int(registration["budget"]["maximum_total_tokens"]),
        maximum_cost_usd=float(registration["budget"]["maximum_estimated_cost_usd"]),
    )
    for usage_path in sorted((run_root / "usage").rglob("*.json")) if (run_root / "usage").is_dir() else []:
        budget.record(json.loads(usage_path.read_text(encoding="utf-8")))
    runner = HermesRunner(binary=binary, root=run_root, provider=provider, model=model, budget=budget)
    if credential_env_file is not None:
        destination = runner.home / ".env"
        if not destination.exists():
            shutil.copyfile(credential_env_file, destination)
    if not os.environ.get("DEEPSEEK_API_KEY") and not (runner.home / ".env").is_file():
        raise RuntimeError("DeepSeek credentials must be supplied through the environment or an external .env file")
    runner.require_version()

    restore_root = run_root / "restore"
    public_restore = _restore_once(
        runner,
        image=public["document"],
        target=ARM_PROFILES["public_restored"],
        report_path=restore_root / "public-restored.json",
    )
    _prepare_fresh_profile(runner)
    surfaces = {arm: runner.verify_profile_surface(profile) for arm, profile in ARM_PROFILES.items()}
    required_state = [str(item) for item in registration["success"]["required_restored_state_files_match_public_image"]]
    state = _state_comparison(runner, public["document"], required_state)

    metadata_path = run_root / "metadata.json"
    metadata = {
        "experiment": EXPERIMENT_ID,
        "started_at": utc_now(),
        "git_commit": commit,
        "preregistration_digest": file_digest(preregistration_path),
        "artifacts": {
            "public": {"image_digest": public["image_digest"], "file_digest": public["file_digest"]},
        },
        "model": _model_record(runner),
    }
    if metadata_path.is_file():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        comparable = {key: metadata[key] for key in ("experiment", "git_commit", "preregistration_digest", "artifacts", "model")}
        if any(existing.get(key) != value for key, value in comparable.items()):
            raise RuntimeError("resume metadata does not match the frozen comparison")
        metadata["started_at"] = existing["started_at"]
    else:
        write_json(metadata_path, metadata)

    evaluation = registration["evaluation"]
    scenarios = generate_scenarios(
        "hero",
        int(evaluation["held_out_scenarios"]),
        int(evaluation["scenario_seed"]),
        policies=COHORT_POLICIES,
    )
    schedule = comparison_schedule(
        scenarios=scenarios,
        repetitions=int(evaluation["repetitions_per_scenario"]),
        seed=int(evaluation["schedule_seed"]),
    )
    rows_by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARM_PROFILES}
    results_path = run_root / "evaluation" / "results.jsonl"
    persisted = {}
    if results_path.is_file():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            persisted[str(row["call_id"])] = row

    for index, item in enumerate(schedule, start=1):
        arm = str(item["arm"])
        scenario = item["scenario"]
        repetition = int(item["repetition"])
        call_id = f"{index:03d}-{arm}-{scenario.id}-r{repetition}"
        if call_id in persisted:
            row = persisted[call_id]
            rows_by_arm[arm].append(row)
            runner.emit_progress(phase="hero_comparison", completed=index, total=len(schedule), recovered=True)
            continue
        raw, usage, recovered = runner.complete(
            profile=ARM_PROFILES[arm],
            prompt=decision_prompt(scenario),
            call_id=call_id,
        )
        error: str | None = None
        try:
            decision = parse_decision(raw)
            score = evaluate_decision(scenario, decision, COHORT_POLICIES)
        except (ValueError, json.JSONDecodeError) as caught:
            decision = None
            score = invalid_response_score(scenario, COHORT_POLICIES)
            error = f"{type(caught).__name__}: {caught}"
        row = {
            "call_id": call_id,
            "arm": arm,
            "repetition": repetition,
            "scenario": asdict(scenario),
            "decision": None if decision is None else asdict(decision),
            "score": asdict(score),
            "parse_error": error,
            "model": _model_record(runner),
            "usage": usage,
            "raw_response": _response_reference(runner, call_id, raw),
        }
        append_jsonl(results_path, row)
        rows_by_arm[arm].append(row)
        runner.emit_progress(phase="hero_comparison", completed=index, total=len(schedule), recovered=recovered)

    summaries = {arm: aggregate(rows) for arm, rows in rows_by_arm.items()}
    verdict = analyze_hero_result(summaries, thresholds=registration["success"], state_equal=bool(state["all_equal"]))
    source_after = file_digest(public_image)
    if source_before != source_after:
        raise RuntimeError("source image changed during comparison")
    evidence = {
        "experiment": EXPERIMENT_ID,
        "started_at": metadata["started_at"],
        "completed_at": utc_now(),
        "git_commit": commit,
        "preregistration": {
            "path": preregistration_path.relative_to(repository).as_posix(),
            "digest": file_digest(preregistration_path),
            "status": registration["status"],
        },
        "artifacts": {
            "private_trained_parent": {
                "image_digest": registration["artifacts"]["private_trained_parent"]["image_digest"],
                "use": "lineage_only_not_sent_to_provider",
            },
            "public_restored": {
                "image_digest": public["image_digest"],
                "file_digest": public["file_digest"],
                "source_immutable": source_before == source_after,
            },
            "prior_gate_e_evidence": registration["artifacts"]["prior_gate_e_evidence"],
        },
        "model": _model_record(runner),
        "harness_prompt_surfaces": surfaces,
        "restore": {"public_restored": public_restore},
        "developed_state": state,
        "evaluation": {
            "synthetic": True,
            "held_out_scenarios": len(scenarios),
            "repetitions_per_scenario": int(evaluation["repetitions_per_scenario"]),
            "schedule": "globally_seeded_interleaving",
            "summaries": summaries,
        },
        "budget": budget.as_dict(),
        "privacy": {
            "real_user_data": False,
            "raw_responses": "private_local_only",
            "credentials_in_images": False,
        },
        "verdict": verdict,
        "claim": (
            "The public Hermes image retained the bounded mission-specific developed state after fresh restore."
            if verdict["passed"]
            else "The public Hermes image did not pass the preregistered state-retention comparison; the negative result is retained."
        ),
        "limitations": [
            "Synthetic procurement world only.",
            "Same-harness state retention only; no cross-harness behavioral portability claim.",
            "This comparison does not establish real-world negotiation competence.",
        ],
    }
    write_json(run_root / "final-evidence.json", evidence)
    write_json(public_json, evidence)
    _write_public_markdown(public_markdown, evidence)
    print(json.dumps(verdict, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if verdict["passed"] else 2


def build_parser(repository: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare the public hero image against a same-model fresh Agent")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--public-image", type=Path, required=True)
    parser.add_argument(
        "--preregistration",
        type=Path,
        default=repository / "experiments" / "situated_negotiation_ground" / "hero_preregistration.yaml",
    )
    parser.add_argument(
        "--public-json",
        type=Path,
        default=repository / "docs" / "evidence" / "public-hero-restore-comparison-2026-08-26.json",
    )
    parser.add_argument(
        "--public-markdown",
        type=Path,
        default=repository / "docs" / "evidence" / "public-hero-restore-comparison-2026-08-26.md",
    )
    parser.add_argument("--hermes", type=Path, default=repository / ".venv-hermes" / "Scripts" / "hermes.exe")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--credential-env-file", type=Path)
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    repository = Path(__file__).resolve().parents[2]
    args = build_parser(repository).parse_args(argv)
    try:
        return execute(
            repository=repository,
            run_root=args.run_root,
            public_image=args.public_image,
            preregistration_path=args.preregistration,
            public_json=args.public_json,
            public_markdown=args.public_markdown,
            binary=args.hermes,
            provider=str(args.provider),
            model=str(args.model),
            resume=bool(args.resume),
            credential_env_file=args.credential_env_file,
        )
    except AgentImageError as error:
        print(json.dumps(error.as_dict(), ensure_ascii=False, sort_keys=True), flush=True)
        return 1
    except Exception as error:
        print(
            json.dumps(
                {"error": {"code": "E_HERO_COMPARISON_FAILED", "message": f"{type(error).__name__}: {error}"}},
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
