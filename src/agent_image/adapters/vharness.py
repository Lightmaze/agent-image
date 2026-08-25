from __future__ import annotations

import gzip
import io
import json
import os
import re
import shutil
import socket
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Protocol

from agent_image import __version__
from agent_image.adapter_contract import AdapterExport
from agent_image.canonical import canonical_json_bytes, sha256_bytes
from agent_image.container import MAX_ENTRIES, MAX_FILE_SIZE, MAX_TOTAL_SIZE
from agent_image.errors import AgentImageError
from agent_image.image_archive import ImageDocument, layer_root_digest
from agent_image.paths import validate_archive_path
from agent_image.scanner import secret_filename_reason, structured_secret_findings


VH_VERSION = "0.1.0-alpha.1"
VH_PNPM = "11.7.0"
VH_NODE = "24.15.0"
VH_NATIVE_MEDIA_TYPE = "application/vnd.vharness.agent-image-instance.v0.1.0-alpha.1+tar+gzip"
REFERENCE_RUNTIME = "agent-image.reference-persistent"
INSTANCE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
INSTANCE_FILES = ("vhd-config.json", "guest-state.json", "reference-guest.mjs")
SOURCE_DIGEST_EXCLUDED = {".git", "node_modules", "dist", "coverage", ".tmp", ".pytest-tmp"}


@dataclass(frozen=True)
class VHarnessPin:
    version: str = VH_VERSION
    node: str = VH_NODE
    pnpm: str = VH_PNPM


class VHarnessRuntime(Protocol):
    def contract(self) -> dict[str, str]: ...
    def home(self) -> Path: ...
    def instance_path(self, name: str) -> Path: ...
    def validate_config(self, config: Path) -> dict[str, Any]: ...
    def validate_live(self, instance: Path, *, image_digest: str, expected_items_digest: str) -> dict[str, Any]: ...
    def remove_instance(self, name: str) -> None: ...


class SubprocessVHarnessRuntime:
    def __init__(
        self,
        *,
        source_root: Path,
        node_binary: str,
        vharness_home: Path | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.source_root = source_root.expanduser().resolve()
        self.node_binary = str(Path(node_binary).expanduser().resolve())
        self.vharness_home = vharness_home
        self.environment = dict(environment or {})
        self.timeout_seconds = timeout_seconds

    @property
    def cli_entry(self) -> Path:
        return self.source_root / "packages" / "cli" / "dist" / "bin.js"

    @property
    def vhd_entry(self) -> Path:
        return self.source_root / "packages" / "vhd" / "dist" / "bin.js"

    def home(self) -> Path:
        configured = self.vharness_home or Path(os.environ.get("VH_AGENT_IMAGE_HOME", ""))
        if str(configured).strip():
            return configured.expanduser().resolve()
        return (Path.home() / ".vharness" / "agent-image").resolve()

    def instance_path(self, name: str) -> Path:
        return (self.home() / "instances" / name).resolve()

    def _environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment.update(self.environment)
        environment.setdefault("NO_COLOR", "1")
        return environment

    def _run_cli(self, arguments: list[str], *, error_code: str = "E_NATIVE_INCOMPATIBLE") -> dict[str, Any]:
        if not Path(self.node_binary).is_file() or not self.cli_entry.is_file():
            raise AgentImageError("E_ADAPTER_NOT_FOUND", "Pinned Node or vHarness CLI build was not found.")
        try:
            result = subprocess.run(
                [self.node_binary, str(self.cli_entry), *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.source_root,
                env=self._environment(),
                timeout=self.timeout_seconds,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            raise AgentImageError(error_code, f"vHarness CLI failed to run: {error}") from error
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip() or f"vHarness CLI exited with {result.returncode}."
            raise AgentImageError(error_code, message, details={"arguments": arguments})
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise AgentImageError(error_code, "vHarness CLI emitted invalid JSON.") from error
        if not isinstance(value, dict):
            raise AgentImageError(error_code, "vHarness CLI response must be an object.")
        return value

    def contract(self) -> dict[str, str]:
        package_path = self.source_root / "package.json"
        lock_path = self.source_root / "pnpm-lock.yaml"
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AgentImageError("E_ADAPTER_NOT_FOUND", "vHarness package.json is unavailable or invalid.") from error
        if package.get("version") != VH_VERSION or package.get("packageManager") != f"pnpm@{VH_PNPM}":
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                f"vHarness must be exactly {VH_VERSION} with pnpm {VH_PNPM}.",
            )
        if not lock_path.is_file() or not self.cli_entry.is_file() or not self.vhd_entry.is_file():
            raise AgentImageError("E_ADAPTER_NOT_FOUND", "Pinned vHarness build or lockfile is incomplete.")
        return {
            "version": VH_VERSION,
            "node": VH_NODE,
            "pnpm": VH_PNPM,
            "source_tree_digest": _tree_digest(self.source_root),
            "runtime_build_digest": _build_digest(self.source_root),
            "lockfile_digest": sha256_bytes(lock_path.read_bytes()),
        }

    def validate_config(self, config: Path) -> dict[str, Any]:
        result = self._run_cli(["validate", str(config.resolve())], error_code="E_SOURCE_UNSUPPORTED")
        if result.get("valid") is not True:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "vHarness config validation failed.")
        return result

    def validate_live(self, instance: Path, *, image_digest: str, expected_items_digest: str) -> dict[str, Any]:
        config = instance / "vhd-config.json"
        state_path = instance / "guest-state.json"
        state = _read_json(state_path, "reference Guest state")
        state.setdefault("provenance", {})["sourceImageDigest"] = image_digest
        state_path.write_bytes(_pretty_json(state))
        if _items_digest(state) != expected_items_digest:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Restored Guest items changed before live validation.")

        state_dir = instance / "host-state"
        port = _unused_loopback_port()
        process = subprocess.Popen(
            [
                self.node_binary,
                str(self.vhd_entry),
                "serve",
                "--config",
                str(config),
                "--state-dir",
                str(state_dir),
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=self.source_root,
            env=self._environment(),
        )
        token_file = state_dir / "host-api.token"
        url = f"http://127.0.0.1:{port}"
        try:
            _wait_for_vhd(process, url, token_file, self.timeout_seconds)
            common = ["--url", url, "--token-file", str(token_file)]
            initial = self._run_cli(["status", *common])
            first = self._run_cli(["transition", "audit", *common, "--actor", "agent-image:restore"])
            second = self._run_cli(["transition", "wake", *common, "--actor", "agent-image:restore"])
            final = self._run_cli(["status", *common])
            journal = self._run_cli(["journal", *common])
        finally:
            _stop_process(process)

        restored_state = _read_json(state_path, "restored reference Guest state")
        if restored_state.get("currentRegime") != "wake":
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Live Guest did not return to the source regime.")
        if _items_digest(restored_state) != expected_items_digest:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Live vHarness round-trip changed Agent state items.")
        final_state = final.get("state", {})
        if final_state.get("regimeMachine", {}).get("currentRegime") != "wake":
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "vhd did not return to the source regime.")
        if first.get("applied", {}).get("transition", {}).get("outcome") != "committed" or second.get(
            "applied", {}
        ).get("transition", {}).get("outcome") != "committed":
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Live vHarness restore transitions did not commit.")
        grants = final_state.get("authorityLedger", {}).get("grants", [])
        if not grants or any(not str(grant.get("grantedBy", "")).startswith("vhd:") for grant in grants):
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Restored authority was not freshly granted by vhd.")
        loss_reports = final_state.get("lossReports", {})
        if not loss_reports or any(report.get("complete") is not True for report in loss_reports.values()):
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Host lacks complete typed loss evidence.")
        if any(
            loss.get("authorityChange") == "escalation"
            for report in loss_reports.values()
            for loss in report.get("losses", [])
        ):
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Host recorded an authority escalation.")
        if any(
            set(report.get("sourceStateClasses", [])) != set(report.get("mappedStateClasses", []))
            or any(loss.get("severity") == "blocking" for loss in report.get("losses", []))
            for report in loss_reports.values()
        ):
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Host recorded incomplete or blocking state transfer loss.")
        records = journal.get("records", [])
        provenance_fact = f"source-image:{image_digest}"
        if not any(
            provenance_fact in record.get("payload", {}).get("evidence", {}).get("facts", [])
            for record in records
            if record.get("type") == "driver.evidence.recorded"
        ):
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Host journal did not retain source image provenance.")
        if not isinstance(final_state.get("kernelId"), str) or not final_state["kernelId"]:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "vhd did not expose a target kernel identity.")
        return {
            "kernel_id": final_state.get("kernelId"),
            "journal_head": final_state.get("journalHead"),
            "host_current_regime": final_state.get("regimeMachine", {}).get("currentRegime"),
            "guest_current_regime": restored_state.get("currentRegime"),
            "state_items_digest": expected_items_digest,
            "fresh_authority": True,
            "authority_grant_count": len(grants),
            "loss_report_count": len(loss_reports),
            "source_image_provenance_recorded": True,
            "security_boundary": final.get("securityBoundary"),
        }

    def remove_instance(self, name: str) -> None:
        path = self.instance_path(name)
        root = (self.home() / "instances").resolve()
        if path.parent.resolve() != root or not path.is_dir():
            raise AgentImageError("E_ROLLBACK_FAILED", f"Refusing to remove unexpected vHarness path: {path}")
        shutil.rmtree(path)


def _name(value: str, *, target: bool = False) -> str:
    normalized = value.strip().lower()
    if not INSTANCE_NAME.fullmatch(normalized):
        code = "E_NATIVE_INCOMPATIBLE" if target else "E_SOURCE_NOT_FOUND"
        raise AgentImageError(code, f"Invalid vHarness instance name: {value!r}")
    return normalized


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", f"Invalid {label}: {path}") from error
    if not isinstance(value, dict):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", f"{label} must be an object.")
    return value


def _pretty_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _items_digest(state: Mapping[str, Any]) -> str:
    items = state.get("items")
    if not isinstance(items, list):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "Reference Guest state must contain an items array.")
    return sha256_bytes(canonical_json_bytes(items))


def _tree_digest(root: Path) -> str:
    entries: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SOURCE_DIGEST_EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        entries.append({"path": relative.as_posix(), "digest": sha256_bytes(path.read_bytes())})
    return sha256_bytes(canonical_json_bytes(entries))


def _build_digest(root: Path) -> str:
    entries: list[dict[str, str]] = []
    for path in sorted((root / "packages").glob("*/dist/*")):
        if path.is_symlink() or not path.is_file() or path.name == ".tsbuildinfo":
            continue
        entries.append({"path": path.relative_to(root).as_posix(), "digest": sha256_bytes(path.read_bytes())})
    if not entries:
        raise AgentImageError("E_ADAPTER_NOT_FOUND", "vHarness runtime build artifacts were not found.")
    return sha256_bytes(canonical_json_bytes(entries))


def _instance_files(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"vHarness instance does not exist: {root}")
    unexpected = [path.name for path in root.iterdir() if path.name not in INSTANCE_FILES]
    if unexpected:
        raise AgentImageError(
            "E_SOURCE_UNSUPPORTED",
            "vHarness export requires a stopped portable instance with no Host state directory.",
            details={"unexpected": sorted(unexpected)},
        )
    entries: dict[str, bytes] = {}
    total = 0
    for name in INSTANCE_FILES:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise AgentImageError("E_SOURCE_UNSUPPORTED", f"Missing regular vHarness instance file: {name}")
        data = path.read_bytes()
        if len(data) > MAX_FILE_SIZE or total + len(data) > MAX_TOTAL_SIZE:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", f"vHarness source item exceeds size limits: {name}")
        total += len(data)
        filename = secret_filename_reason(name)
        keys = structured_secret_findings(name, "application/json" if name.endswith(".json") else "text/javascript", data)
        if filename or keys:
            raise AgentImageError(
                "E_SECRET_DETECTED",
                f"Secret material cannot enter a vHarness image: {name}",
                details={"filename": filename, "structured_keys": keys},
            )
        entries[name] = data
    return entries


def _validate_reference_instance(entries: Mapping[str, bytes]) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        config = json.loads(entries["vhd-config.json"].decode("utf-8", errors="strict"))
        state = json.loads(entries["guest-state.json"].decode("utf-8", errors="strict"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "vHarness native JSON is invalid.") from error
    if config.get("mockPointId") or config.get("realization", {}).get("spec", {}).get("runtimeFamily") != REFERENCE_RUNTIME:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "vHarness P1 accepts only the non-mock reference persistent runtime.")
    driver = config.get("driver", {})
    if driver != {"entry": "reference-guest.mjs", "fixture": "guest-state.json"}:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "vHarness reference driver paths must be relative and pinned.")
    binding = config.get("realization", {}).get("spec", {}).get("runtimeBinding", {})
    if binding.get("credentialRef") != "none":
        raise AgentImageError("E_SECRET_DETECTED", "vHarness credentialRef must be 'none' for portable export.")
    native = config.get("realization", {}).get("spec", {}).get("native", {})
    if native.get("productionAllowed") is not True:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "vHarness reference realization is not production-allowed.")
    if state.get("apiVersion") != "agent-image.reference-guest/v1" or not isinstance(state.get("items"), list):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "Reference Guest state is malformed.")
    if state.get("currentRegime") != config.get("harnessSet", {}).get("spec", {}).get("initialRegime"):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "Stopped Guest regime must equal the Harness Set initial regime.")
    ids: set[str] = set()
    classes: set[str] = set()
    for item in state["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in ids:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Reference Guest items require unique string ids.")
        if item.get("sensitivity") not in {"public", "internal", "private"}:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Reference Guest item sensitivity is invalid.")
        if item.get("transferType") not in {
            "ContextTransfer", "MemoryTransfer", "PendingIntentTransfer", "PlasticityDelta"
        }:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Reference Guest transfer type is invalid.")
        if not isinstance(item.get("semanticClass"), str) or item["semanticClass"] in classes:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Reference Guest semantic classes must be unique.")
        ids.add(item["id"])
        classes.add(item["semanticClass"])
    return config, state


def _tar_bytes(entries: Mapping[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path, data in sorted(entries.items()):
            safe = validate_archive_path(path)
            info = tarfile.TarInfo(safe)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as compressed:
        compressed.write(raw.getvalue())
    return output.getvalue()


def _read_native(data: bytes) -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) > MAX_ENTRIES:
                raise AgentImageError("E_IMAGE_CORRUPT", "vHarness native archive has too many entries.")
            for member in members:
                path = validate_archive_path(member.name)
                if path in entries:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Duplicate vHarness native member: {path}")
                if PureWindowsPath(path).is_absolute() or not member.isfile() or member.issym() or member.islnk():
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Unsafe vHarness native member: {path}")
                if member.size < 0 or member.size > MAX_FILE_SIZE or total + member.size > MAX_TOTAL_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Oversized vHarness native member: {path}")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Unreadable vHarness native member: {path}")
                payload = extracted.read()
                total += len(payload)
                entries[path] = payload
    except AgentImageError:
        raise
    except (tarfile.TarError, OSError, EOFError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", "Invalid vHarness native archive.") from error
    return entries


def _write_instance(root: Path, entries: Mapping[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=False)
    for relative, data in sorted(entries.items()):
        safe = validate_archive_path(relative)
        if PureWindowsPath(safe).is_absolute():
            raise AgentImageError("E_IMAGE_CORRUPT", f"Absolute vHarness target path: {safe}")
        target = root / Path(*PurePosixPath(safe).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _inventory_digest(entries: Mapping[str, bytes]) -> str:
    return sha256_bytes(canonical_json_bytes([
        {"path": path, "digest": sha256_bytes(data)} for path, data in sorted(entries.items())
    ]))


def _loss_summary(outcomes: list[dict[str, Any]]) -> dict[str, int]:
    return {action: sum(item["action"] == action for item in outcomes) for action in (
        "preserved", "transformed", "redacted", "unsupported", "dropped_by_user"
    )}


def _unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_vhd(process: subprocess.Popen[str], url: str, token_file: Path, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().strip() if process.stderr else ""
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"vhd exited before readiness: {stderr}")
        if token_file.is_file():
            try:
                with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError):
                pass
        time.sleep(0.05)
    raise AgentImageError("E_NATIVE_INCOMPATIBLE", "vhd readiness timed out.")


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


class VHarnessAdapter:
    id = "org.agentimage.vharness"
    version = "0.1.0"
    locator_prefix = "vharness"

    def __init__(self, runtime: VHarnessRuntime | None = None) -> None:
        self.runtime = runtime

    def _runtime(self) -> VHarnessRuntime:
        if self.runtime is None:
            raise AgentImageError(
                "E_ADAPTER_NOT_FOUND",
                "vHarness operations require --vharness-source-root and --vharness-node-binary.",
            )
        return self.runtime

    def capabilities(self) -> dict[str, Any]:
        return {
            "archive": True,
            "native_restore": True,
            "semantic_migration": False,
            "portability_level": "P1",
            "pinned_harness": {"version": VH_VERSION, "node": VH_NODE, "pnpm": VH_PNPM},
            "scope": "non-mock reference persistent process guest",
        }

    def inspect_source(self, source: str) -> dict[str, Any]:
        runtime = self._runtime()
        contract = runtime.contract()
        name = _name(source)
        root = runtime.instance_path(name)
        entries = _instance_files(root)
        runtime.validate_config(root / "vhd-config.json")
        _validate_reference_instance(entries)
        return {
            "adapter": {"id": self.id, "version": self.version},
            "source_harness": {"id": "vharness", "version": contract["version"]},
            "source": {"name": name, "path": str(root), "digest": _inventory_digest(entries)},
            "inventory_count": len(entries),
            "capabilities": self.capabilities(),
        }

    def export(
        self,
        source: str,
        policy: str,
        *,
        include_experience: bool = False,
        include_workspace: bool = False,
    ) -> AdapterExport:
        del include_experience, include_workspace
        if policy not in {"private", "public"}:
            raise AgentImageError("E_SPEC_INVALID", f"Unsupported export policy: {policy}")
        runtime = self._runtime()
        contract = runtime.contract()
        name = _name(source)
        root = runtime.instance_path(name)
        entries = _instance_files(root)
        before = _inventory_digest(entries)
        runtime.validate_config(root / "vhd-config.json")
        config, state = _validate_reference_instance(entries)
        after_entries = _instance_files(root)
        after = _inventory_digest(after_entries)
        if before != after:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "vHarness source changed during read-only export.")

        outcomes: list[dict[str, Any]] = []
        for path in INSTANCE_FILES:
            action = "redacted" if policy == "public" else ("transformed" if path == "guest-state.json" else "preserved")
            reason = (
                "vHarness native state is private by default"
                if policy == "public"
                else "restore binds source image provenance while preserving all Agent state items"
                if path == "guest-state.json"
                else "preserved byte-for-byte in the typed vHarness native layer"
            )
            outcomes.append({"id": f"source-file-{path}", "source": f"instance/{path}", "action": action, "reason": reason})
        for item in state["items"]:
            outcomes.append({
                "id": f"source-state-{item['id']}",
                "source": f"guest-state/items/{item['id']}",
                "action": "redacted" if policy == "public" else "preserved",
                "reason": "private native Agent state" if policy == "public" else "embedded state item retained exactly",
            })
        outcomes.append({
            "id": "source-host-authority",
            "source": "host/authority",
            "action": "redacted",
            "reason": "Host grants and Host API credentials never enter an Agent Image",
        })

        layers: list[dict[str, Any]] = []
        payloads: dict[str, bytes] = {}
        if policy == "private":
            metadata = {
                "source_name": name,
                "source_instance_digest": before,
                "state_items_digest": _items_digest(state),
                "initial_regime": config["harnessSet"]["spec"]["initialRegime"],
                "source_tree_digest": contract["source_tree_digest"],
            }
            native = _tar_bytes({**entries, "meta/instance.json": _pretty_json(metadata)})
            path = "layers/native/vharness-instance.tar.gz"
            payloads[path] = native
            layers.append({
                "id": "vharness-native-instance",
                "kind": "native",
                "media_type": VH_NATIVE_MEDIA_TYPE,
                "path": path,
                "digest": sha256_bytes(native),
                "size": len(native),
                "privacy": "private",
                "portability": "opaque",
                "source": {
                    "origin": f"vharness:{name}",
                    "reason": "Harness Set, Runtime Realization, reference Guest code, and persistent Agent state",
                },
            })
        manifest: dict[str, Any] = {
            "spec": "agent-image/v0.1",
            "image": {
                "name": name,
                "version": "0.1.0",
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "digest": layer_root_digest(layers),
                "description": f"vHarness reference persistent instance exported through {self.id}",
            },
            "runtime": {
                "harness": {"id": "vharness", "version": contract["version"]},
                "adapter": {"id": self.id, "version": self.version},
            },
            "layers": layers,
            "privacy": {"default": "private", "public_build": policy == "public", "unresolved_items": 0},
            "provenance": {
                "source_harness": "vharness",
                "source_adapter": self.id,
                "export_tool_version": __version__,
                "source_uri": f"vharness:{name}",
            },
            "extensions": {
                "org.agentimage.vharness.contract": {
                    **contract,
                    "source_instance_digest": before,
                    "state_items_digest": _items_digest(state),
                    "runtime_family": REFERENCE_RUNTIME,
                    "authority_exported": False,
                }
            },
        }
        report = {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "build",
            "adapter": {"id": self.id, "version": self.version},
            "inventory_count": len(outcomes),
            "outcomes": outcomes,
            "loss_summary": _loss_summary(outcomes),
        }
        return AdapterExport(manifest=manifest, payloads=payloads, source_report=report)

    def native_restore(self, image: ImageDocument, target: str) -> dict[str, Any]:
        runtime = self._runtime()
        contract = runtime.contract()
        name = _name(target, target=True)
        target_path = runtime.instance_path(name)
        if target_path.exists():
            raise AgentImageError("E_TARGET_EXISTS", f"vHarness target already exists: {name}")
        harness = image.manifest.get("runtime", {}).get("harness", {})
        if harness != {"id": "vharness", "version": contract["version"]}:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Image is not compatible with pinned vHarness.")
        extension = image.manifest.get("extensions", {}).get("org.agentimage.vharness.contract", {})
        if extension.get("source_tree_digest") != contract["source_tree_digest"]:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "vHarness source tree digest drifted from the image contract.")
        native_layers = [
            layer for layer in image.manifest["layers"]
            if layer["kind"] == "native" and layer["media_type"] == VH_NATIVE_MEDIA_TYPE
        ]
        if len(native_layers) != 1:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "vHarness P1 requires one pinned native layer.")
        entries = _read_native(image.entries[native_layers[0]["path"]])
        try:
            metadata = json.loads(entries.pop("meta/instance.json").decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AgentImageError("E_IMAGE_CORRUPT", "vHarness native metadata is invalid.") from error
        if set(entries) != set(INSTANCE_FILES):
            raise AgentImageError("E_IMAGE_CORRUPT", "vHarness native layer contains an unknown or missing file.")
        _, state = _validate_reference_instance(entries)
        if metadata.get("state_items_digest") != _items_digest(state) or extension.get(
            "state_items_digest"
        ) != _items_digest(state):
            raise AgentImageError("E_IMAGE_CORRUPT", "vHarness state item digest does not reconcile.")
        created = False
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            _write_instance(target_path, entries)
            created = True
            runtime.validate_config(target_path / "vhd-config.json")
            live = runtime.validate_live(
                target_path,
                image_digest=image.manifest["image"]["digest"],
                expected_items_digest=metadata["state_items_digest"],
            )
        except Exception as error:
            if created or target_path.exists():
                try:
                    runtime.remove_instance(name)
                except Exception as rollback_error:
                    raise AgentImageError(
                        "E_ROLLBACK_FAILED",
                        f"vHarness target rollback was incomplete: {name}",
                        details={"original_error": str(error), "rollback_error": str(rollback_error)},
                    ) from error
            raise
        source_report = image.json_entry("meta/source-report.json")
        outcomes: list[dict[str, Any]] = []
        for source_item in source_report["outcomes"]:
            action = source_item["action"]
            if source_item["source"] == "instance/guest-state.json" and action == "transformed":
                action, reason = "transformed", "source image provenance bound; all Agent state item digests preserved"
            elif action == "preserved":
                reason = "native source file or state item preserved and live-validated"
            else:
                reason = source_item["reason"]
            outcomes.append({**source_item, "action": action, "reason": reason})
        return {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "restore",
            "adapter": {"id": self.id, "version": self.version},
            "target": f"vharness:{name}",
            "target_instance": str(target_path),
            "inventory_count": len(outcomes),
            "outcomes": outcomes,
            "loss_summary": _loss_summary(outcomes),
            "layer_inventory_count": 1,
            "layer_outcomes": [{
                "id": native_layers[0]["id"],
                "action": "preserved",
                "reason": "typed native state restored through a fresh vhd authority domain and live Guest round-trip",
            }],
            "live_validation": live,
            "source_tree_digest": contract["source_tree_digest"],
            "validated": True,
            "portability": "P1",
            "harness": {"id": "vharness", "version": contract["version"]},
        }
