from __future__ import annotations

import gzip
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
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


@dataclass(frozen=True)
class OpenClawPin:
    version: str
    tag: str
    commit: str
    node: str
    npm: str


OPENCLAW_PIN = OpenClawPin(
    version="2026.7.1-2",
    tag="v2026.7.1-2",
    commit="0790d9f",
    node="24.15.0",
    npm="11.12.1",
)
OPENCLAW_NATIVE_MEDIA_TYPE = "application/vnd.openclaw.agent.v2026.7.1-2+tar+gzip"
AGENT_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class OpenClawAgent:
    id: str
    workspace: Path
    agent_dir: Path


class OpenClawCLI(Protocol):
    def version(self) -> str: ...
    def list_agents(self) -> list[OpenClawAgent]: ...
    def show_agent(self, name: str) -> OpenClawAgent: ...
    def target_workspace(self, name: str) -> Path: ...
    def add_agent(self, name: str, workspace: Path) -> OpenClawAgent: ...
    def delete_agent(self, name: str) -> None: ...


class SubprocessOpenClawCLI:
    def __init__(
        self,
        binary: str = "openclaw",
        *,
        node_binary: str | None = None,
        environment: Mapping[str, str] | None = None,
        workspace_root: Path | None = None,
        timeout_seconds: int = 180,
    ) -> None:
        self.binary = binary
        self.node_binary = node_binary
        self.environment = dict(environment or {})
        self.workspace_root = workspace_root
        self.timeout_seconds = timeout_seconds

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(self.environment)
        env.setdefault("NO_COLOR", "1")
        return env

    def _run(self, arguments: list[str], *, error_code: str) -> subprocess.CompletedProcess[str]:
        command = self._command(arguments)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._env(),
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as error:
            raise AgentImageError(
                "E_ADAPTER_NOT_FOUND",
                f"OpenClaw executable was not found: {self.binary}",
            ) from error
        except subprocess.TimeoutExpired as error:
            raise AgentImageError(error_code, f"OpenClaw command timed out: {' '.join(arguments)}") from error
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip() or f"OpenClaw exited with {result.returncode}."
            raise AgentImageError(
                error_code,
                message,
                details={"command": arguments, "exit_code": result.returncode},
            )
        return result

    def _command(self, arguments: list[str]) -> list[str]:
        """Resolve the npm Windows shim without relying on ambient PATH state."""
        if self.node_binary is None:
            return [self.binary, *arguments]
        binary = Path(self.binary).expanduser().resolve()
        if binary.suffix.lower() in {".cmd", ".bat"} and binary.parent.name == ".bin":
            script = binary.parent.parent / "openclaw" / "openclaw.mjs"
        elif binary.suffix.lower() == ".mjs":
            script = binary
        else:
            raise AgentImageError(
                "E_ADAPTER_NOT_FOUND",
                "Explicit OpenClaw Node execution requires openclaw.cmd or openclaw.mjs.",
                details={"binary": str(binary)},
            )
        if not script.is_file():
            raise AgentImageError(
                "E_ADAPTER_NOT_FOUND",
                f"OpenClaw module entry point was not found: {script}",
            )
        return [self.node_binary, str(script), *arguments]

    def version(self) -> str:
        result = self._run(["--version"], error_code="E_SOURCE_UNSUPPORTED")
        match = re.search(r"(?<!\d)(\d{4}\.\d+\.\d+(?:-\d+)?)(?!\d)", f"{result.stdout}\n{result.stderr}")
        if not match:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Could not parse OpenClaw version output.")
        return match.group(1)

    def list_agents(self) -> list[OpenClawAgent]:
        result = self._run(["agents", "list", "--json"], error_code="E_SOURCE_UNSUPPORTED")
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "OpenClaw agents list did not return JSON.") from error
        if not isinstance(value, list):
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "OpenClaw agents list JSON must be an array.")
        agents: list[OpenClawAgent] = []
        for item in value:
            if not isinstance(item, dict) or not all(key in item for key in ("id", "workspace", "agentDir")):
                raise AgentImageError("E_SOURCE_UNSUPPORTED", "OpenClaw returned an incomplete agent record.")
            agents.append(
                OpenClawAgent(
                    id=str(item["id"]),
                    workspace=Path(str(item["workspace"])).expanduser().resolve(),
                    agent_dir=Path(str(item["agentDir"])).expanduser().resolve(),
                )
            )
        return agents

    def show_agent(self, name: str) -> OpenClawAgent:
        for agent in self.list_agents():
            if agent.id == name:
                if not agent.workspace.is_dir():
                    raise AgentImageError(
                        "E_SOURCE_NOT_FOUND",
                        f"OpenClaw workspace does not exist: {agent.workspace}",
                    )
                return agent
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"OpenClaw agent does not exist: {name}")

    def target_workspace(self, name: str) -> Path:
        if self.workspace_root is not None:
            root = self.workspace_root
        else:
            env = self._env()
            configured = env.get("AGENT_IMAGE_OPENCLAW_WORKSPACE_ROOT", "").strip()
            state_dir = env.get("OPENCLAW_STATE_DIR", "").strip()
            if configured:
                root = Path(configured)
            elif state_dir:
                root = Path(state_dir) / "agent-image-workspaces"
            else:
                root = Path.home() / ".openclaw" / "agent-image-workspaces"
        return (root.expanduser().resolve() / name).resolve()

    def add_agent(self, name: str, workspace: Path) -> OpenClawAgent:
        self._run(
            [
                "agents",
                "add",
                name,
                "--workspace",
                str(workspace.resolve()),
                "--non-interactive",
                "--json",
            ],
            error_code="E_NATIVE_INCOMPATIBLE",
        )
        return self.show_agent(name)

    def delete_agent(self, name: str) -> None:
        self._run(["agents", "delete", name, "--force", "--json"], error_code="E_NATIVE_INCOMPATIBLE")


@dataclass(frozen=True)
class _SourceItem:
    scope: str
    path: str
    data: bytes | None
    item_type: str

    @property
    def source(self) -> str:
        if self.item_type == "directory":
            return f"{self.scope}/{self.path.rstrip('/')}/"
        return f"{self.scope}/{self.path}"


def _agent_name(name: str, *, target: bool = False) -> str:
    normalized = name.strip().lower()
    if not AGENT_NAME.fullmatch(normalized) or (target and normalized == "main"):
        code = "E_NATIVE_INCOMPATIBLE" if target else "E_SOURCE_NOT_FOUND"
        raise AgentImageError(code, f"Invalid OpenClaw agent name: {name!r}")
    return normalized


def _media_type(path: str) -> str:
    suffix = PurePosixPath(path).suffix.casefold()
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".toml": "application/toml",
        ".sqlite": "application/vnd.sqlite3",
        ".db": "application/vnd.sqlite3",
    }.get(suffix, "application/octet-stream")


def _tree_items(root: Path, scope: str, *, summarize_git: bool = False) -> list[_SourceItem]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise AgentImageError("E_SOURCE_UNSUPPORTED", f"OpenClaw {scope} path is not a directory: {root}")
    result: list[_SourceItem] = []
    total_size = 0
    for current_text, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current = Path(current_text)
        directory_names.sort()
        file_names.sort()
        relative_root = current.relative_to(root)
        if summarize_git and relative_root == Path(".") and ".git" in directory_names:
            git_path = current / ".git"
            result.append(_SourceItem(scope=scope, path=".git", data=None, item_type="directory"))
            directory_names.remove(".git")
            if git_path.is_symlink():
                result[-1] = _SourceItem(scope=scope, path=".git", data=None, item_type="symlink")
        for directory_name in list(directory_names):
            path = current / directory_name
            if path.is_symlink():
                relative = path.relative_to(root).as_posix()
                result.append(_SourceItem(scope=scope, path=relative, data=None, item_type="symlink"))
                directory_names.remove(directory_name)
        for file_name in file_names:
            path = current / file_name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                result.append(_SourceItem(scope=scope, path=relative, data=None, item_type="symlink"))
                continue
            try:
                size = path.stat().st_size
                if size < 0 or size > MAX_FILE_SIZE or total_size + size > MAX_TOTAL_SIZE:
                    raise AgentImageError(
                        "E_SOURCE_UNSUPPORTED",
                        f"OpenClaw source item exceeds Agent Image size limits: {scope}/{relative}",
                    )
                data = path.read_bytes()
            except AgentImageError:
                raise
            except OSError as error:
                raise AgentImageError(
                    "E_SOURCE_UNSUPPORTED",
                    f"Cannot read OpenClaw source item: {scope}/{relative}",
                ) from error
            total_size += size
            result.append(_SourceItem(scope=scope, path=relative, data=data, item_type="file"))
        if len(result) > MAX_ENTRIES:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "OpenClaw source inventory exceeds entry limits.")
    return result


def _source_items(agent: OpenClawAgent) -> list[_SourceItem]:
    result = [_SourceItem(scope="registration", path=agent.id, data=None, item_type="virtual")]
    result.extend(_tree_items(agent.workspace, "workspace", summarize_git=True))
    result.extend(_tree_items(agent.agent_dir, "agent"))
    result.extend(_tree_items(agent.agent_dir.parent / "sessions", "sessions"))
    return sorted(result, key=lambda item: (item.scope, item.path, item.item_type))


def _inventory_digest(items: list[_SourceItem]) -> str:
    values = [
        {
            "source": item.source,
            "type": item.item_type,
            "digest": sha256_bytes(item.data) if item.data is not None else item.item_type,
        }
        for item in items
    ]
    return sha256_bytes(canonical_json_bytes(values))


def _secret_findings(item: _SourceItem) -> tuple[str | None, list[str]]:
    source = item.source.casefold()
    if item.scope == "agent" and (
        item.path.casefold().startswith("codex-home/")
        or PurePosixPath(item.path).name.casefold() == "auth-profiles.json"
    ):
        return "OpenClaw authentication/runtime account state is forbidden", []
    filename = secret_filename_reason(item.source)
    keys: list[str] = []
    if item.data is not None:
        keys = structured_secret_findings(item.path, _media_type(item.path), item.data)
    if "credential" in source or "/auth" in source:
        filename = filename or "OpenClaw credential/auth state is forbidden"
    return filename, keys


def _logical_kind(item: _SourceItem, *, include_workspace: bool) -> str | None:
    if item.scope == "sessions":
        return "experience"
    if item.scope != "workspace":
        return None
    path = item.path
    if path in {"SOUL.md", "IDENTITY.md"}:
        return "identity"
    if path in {"USER.md", "MEMORY.md"} or path.startswith("memory/"):
        return "memory"
    if path.startswith("skills/"):
        return "skills"
    if path in {"AGENTS.md", "TOOLS.md", "HEARTBEAT.md", "BOOT.md", "BOOTSTRAP.md"}:
        return "workspace"
    if include_workspace and (path.startswith("canvas/") or path.endswith(".md")):
        return "workspace"
    return None


def _layer_id(kind: str, source: str) -> str:
    return f"openclaw-{kind}-{sha256_bytes(source.encode('utf-8'))[7:19]}"


def _native_archive(source_agent: str, entries: Mapping[str, bytes]) -> bytes:
    values = dict(entries)
    values["meta/agent.json"] = canonical_json_bytes(
        {"source_agent": source_agent, "contract": OPENCLAW_PIN.tag}
    )
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(values):
                data = values[path]
                info = tarfile.TarInfo(name=path)
                info.size = len(data)
                info.mtime = 0
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


def _read_native_archive(data: bytes) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive:
                posix = PurePosixPath(member.name.replace("\\", "/"))
                windows = PureWindowsPath(member.name)
                if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
                    raise AgentImageError("E_UNSAFE_PATH", f"Unsafe OpenClaw native path: {member.name}")
                path = validate_archive_path(posix.as_posix())
                if not member.isfile() or path in result:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Invalid OpenClaw native member: {member.name}")
                if member.size < 0 or member.size > MAX_FILE_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"OpenClaw native item exceeds limits: {path}")
                total += member.size
                if len(result) + 1 > MAX_ENTRIES or total > MAX_TOTAL_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", "OpenClaw native snapshot exceeds limits.")
                stream = archive.extractfile(member)
                if stream is None:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Cannot read OpenClaw native item: {path}")
                value = stream.read(MAX_FILE_SIZE + 1)
                if len(value) != member.size:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"OpenClaw native size mismatch: {path}")
                result[path] = value
    except AgentImageError:
        raise
    except (OSError, EOFError, tarfile.TarError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Cannot read OpenClaw native snapshot: {error}") from error
    return result


def _write_files(root: Path, entries: Mapping[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve()
    for relative, data in sorted(entries.items()):
        safe = validate_archive_path(relative)
        target = (resolved_root / Path(*PurePosixPath(safe).parts)).resolve()
        try:
            target.relative_to(resolved_root)
        except ValueError as error:
            raise AgentImageError("E_UNSAFE_PATH", f"OpenClaw target path escaped its root: {relative}") from error
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise AgentImageError("E_TARGET_EXISTS", f"OpenClaw target item already exists: {target}")
        target.write_bytes(data)


def _cleanup_owned_workspace(path: Path, expected: Path) -> None:
    resolved = path.resolve()
    if resolved != expected.resolve() or resolved.parent == resolved:
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"Refusing cleanup outside owned workspace: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _reset_owned_workspace(path: Path, expected: Path) -> None:
    resolved = path.resolve()
    if resolved != expected.resolve() or not resolved.is_dir() or resolved.parent == resolved:
        raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"Refusing reset outside owned workspace: {resolved}")
    for child in resolved.iterdir():
        if child.name == ".git":
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"Unsupported generated workspace item: {child}")


def _loss_summary(outcomes: list[dict[str, Any]]) -> dict[str, int]:
    result = {key: 0 for key in ("preserved", "transformed", "redacted", "unsupported", "dropped_by_user")}
    for outcome in outcomes:
        result[outcome["action"]] += 1
    return result


class OpenClawAdapter:
    id = "org.agentimage.openclaw"
    version = "0.1.0"

    def __init__(self, cli: OpenClawCLI | None = None) -> None:
        self.cli = cli or SubprocessOpenClawCLI()

    def _require_pin(self) -> str:
        actual = self.cli.version()
        if actual != OPENCLAW_PIN.version:
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                f"OpenClaw {actual} is not the pinned compatibility target {OPENCLAW_PIN.version}.",
                details={"actual": actual, "required": OPENCLAW_PIN.version, "tag": OPENCLAW_PIN.tag},
            )
        return actual

    def capabilities(self) -> dict[str, Any]:
        return {
            "archive": True,
            "native_restore": True,
            "semantic_migration": True,
            "portability_level": "P2-consumer",
            "pinned_harness": {
                "version": OPENCLAW_PIN.version,
                "tag": OPENCLAW_PIN.tag,
                "commit": OPENCLAW_PIN.commit,
                "node": OPENCLAW_PIN.node,
                "npm": OPENCLAW_PIN.npm,
            },
        }

    def agent_digest(self, name: str) -> str:
        agent = self.cli.show_agent(_agent_name(name))
        return _inventory_digest(_source_items(agent))

    def inspect_source(self, source: str) -> dict[str, Any]:
        version = self._require_pin()
        name = _agent_name(source)
        agent = self.cli.show_agent(name)
        inventory = _source_items(agent)
        return {
            "adapter": {"id": self.id, "version": self.version},
            "source_harness": {"id": "openclaw", "version": version},
            "source": {
                "name": name,
                "workspace": str(agent.workspace.resolve()),
                "agent_dir": str(agent.agent_dir.resolve()),
                "digest": _inventory_digest(inventory),
            },
            "inventory_count": len(inventory),
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
        if policy not in {"private", "public"}:
            raise AgentImageError("E_SPEC_INVALID", f"Unsupported export policy: {policy}")
        version = self._require_pin()
        name = _agent_name(source)
        agent = self.cli.show_agent(name)
        before_items = _source_items(agent)
        before = _inventory_digest(before_items)
        for item in before_items:
            filename, keys = _secret_findings(item)
            if filename or keys:
                raise AgentImageError(
                    "E_SECRET_DETECTED",
                    f"Secret material exists in OpenClaw source state: {item.source}",
                    details={"filename": filename, "structured_keys": keys},
                )

        native_entries: dict[str, bytes] = {}
        layers: list[dict[str, Any]] = []
        payloads: dict[str, bytes] = {}
        outcomes: list[dict[str, Any]] = []
        for item in before_items:
            item_id = f"source-{sha256_bytes(item.source.encode('utf-8'))[7:23]}"
            if item.scope == "registration":
                action, reason = "transformed", "agent registration is recreated through the official OpenClaw CLI"
            elif item.item_type in {"symlink", "directory"}:
                action, reason = "unsupported", "symlink and Git metadata are outside the OpenClaw Agent Image contract"
            elif policy == "public":
                action, reason = "redacted", "OpenClaw workspace and runtime state are private by default"
            elif item.scope == "sessions" and not include_experience:
                action, reason = "dropped_by_user", "sessions require explicit --include-experience"
            else:
                action, reason = "preserved", "preserved in the typed OpenClaw native snapshot"
            outcome: dict[str, Any] = {"id": item_id, "action": action, "reason": reason}
            if policy != "public":
                outcome["source"] = item.source
            outcomes.append(outcome)

            if policy != "private" or item.data is None or action not in {"preserved", "transformed"}:
                continue
            native_entries[item.source] = item.data
            kind = _logical_kind(item, include_workspace=include_workspace)
            if kind is None or (kind == "experience" and not include_experience):
                continue
            target = validate_archive_path(f"layers/{kind}/{item.path}")
            payloads[target] = item.data
            layers.append(
                {
                    "id": _layer_id(kind, item.source),
                    "kind": kind,
                    "media_type": _media_type(item.path),
                    "path": target,
                    "digest": sha256_bytes(item.data),
                    "size": len(item.data),
                    "privacy": "private",
                    "portability": "portable",
                    "source": {
                        "path": item.source,
                        "origin": f"openclaw:{name}",
                        "reason": "recognized OpenClaw workspace semantic surface",
                    },
                }
            )

        if policy == "private":
            native = _native_archive(name, native_entries)
            native_path = "layers/native/openclaw-agent.tar.gz"
            payloads[native_path] = native
            layers.append(
                {
                    "id": "openclaw-native-agent",
                    "kind": "native",
                    "media_type": OPENCLAW_NATIVE_MEDIA_TYPE,
                    "path": native_path,
                    "digest": sha256_bytes(native),
                    "size": len(native),
                    "privacy": "private",
                    "portability": "opaque",
                    "source": {
                        "origin": f"openclaw:{name}",
                        "reason": "workspace plus non-secret agent-native state; registration recreated by CLI",
                    },
                }
            )
        after_items = _source_items(self.cli.show_agent(name))
        after = _inventory_digest(after_items)
        if before != after:
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                "OpenClaw source changed during read-only export.",
                details={"before": before, "after": after},
            )
        layers.sort(key=lambda layer: layer["path"])
        manifest: dict[str, Any] = {
            "spec": "agent-image/v0.1",
            "image": {
                "name": name,
                "version": "0.1.0",
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "digest": layer_root_digest(layers),
                "description": f"OpenClaw agent checkpoint exported through {self.id}",
            },
            "runtime": {
                "harness": {"id": "openclaw", "version": version},
                "adapter": {"id": self.id, "version": self.version},
            },
            "layers": layers,
            "privacy": {"default": "private", "public_build": policy == "public", "unresolved_items": 0},
            "provenance": {
                "source_harness": "openclaw",
                "source_adapter": self.id,
                "export_tool_version": __version__,
                "source_uri": f"openclaw:{name}",
            },
            "extensions": {
                "org.agentimage.openclaw.contract": {
                    "version": OPENCLAW_PIN.version,
                    "tag": OPENCLAW_PIN.tag,
                    "commit": OPENCLAW_PIN.commit,
                    "source_agent_digest": before,
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

    def _target_preflight(self, target: str) -> tuple[str, Path]:
        name = _agent_name(target, target=True)
        try:
            self.cli.show_agent(name)
        except AgentImageError as error:
            if error.code != "E_SOURCE_NOT_FOUND":
                raise
        else:
            raise AgentImageError("E_TARGET_EXISTS", f"OpenClaw target already exists: {name}")
        workspace = self.cli.target_workspace(name)
        if workspace.exists():
            raise AgentImageError("E_TARGET_EXISTS", f"OpenClaw target workspace already exists: {workspace}")
        return name, workspace

    def _rollback_created_target(self, name: str, workspace: Path, original: Exception) -> None:
        """Best-effort cleanup that fails loudly if host registration survives."""
        cleanup_errors: list[str] = []
        try:
            self.cli.delete_agent(name)
        except Exception as error:
            cleanup_errors.append(f"official agent deletion failed: {error}")
        if workspace.exists():
            try:
                _cleanup_owned_workspace(workspace, self.cli.target_workspace(name))
            except Exception as error:
                cleanup_errors.append(f"owned workspace cleanup failed: {error}")
        try:
            registered = any(agent.id == name for agent in self.cli.list_agents())
        except Exception as error:
            registered = True
            cleanup_errors.append(f"host registration verification failed: {error}")
        if registered:
            cleanup_errors.append("OpenClaw host registration still exists")
        if workspace.exists():
            cleanup_errors.append("target workspace still exists")
        if cleanup_errors:
            raise AgentImageError(
                "E_ROLLBACK_FAILED",
                f"OpenClaw target rollback was incomplete: {name}",
                details={"original_error": str(original), "residuals": cleanup_errors},
            ) from original

    def native_restore(self, image: ImageDocument, target: str) -> dict[str, Any]:
        version = self._require_pin()
        name, workspace = self._target_preflight(target)
        harness = image.manifest.get("runtime", {}).get("harness", {})
        if harness != {"id": "openclaw", "version": version}:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Image is not compatible with pinned OpenClaw.")
        native_layers = [
            layer
            for layer in image.manifest["layers"]
            if layer["kind"] == "native" and layer["media_type"] == OPENCLAW_NATIVE_MEDIA_TYPE
        ]
        if len(native_layers) != 1:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "OpenClaw P1 requires one pinned native layer.")
        entries = _read_native_archive(image.entries[native_layers[0]["path"]])
        entries.pop("meta/agent.json", None)
        workspace_entries = {
            path.removeprefix("workspace/"): data
            for path, data in entries.items()
            if path.startswith("workspace/")
        }
        agent_entries = {
            path.removeprefix("agent/"): data
            for path, data in entries.items()
            if path.startswith("agent/")
        }
        session_entries = {
            path.removeprefix("sessions/"): data
            for path, data in entries.items()
            if path.startswith("sessions/")
        }
        recognized = len(workspace_entries) + len(agent_entries) + len(session_entries)
        if recognized != len(entries):
            raise AgentImageError("E_IMAGE_CORRUPT", "OpenClaw native snapshot has unknown root entries.")
        created_agent = False
        try:
            agent = self.cli.add_agent(name, workspace)
            created_agent = True
            _reset_owned_workspace(agent.workspace, workspace)
            _write_files(workspace, workspace_entries)
            _write_files(agent.agent_dir, agent_entries)
            _write_files(agent.agent_dir.parent / "sessions", session_entries)
            recognized_agent = self.cli.show_agent(name)
            if recognized_agent.workspace.resolve() != workspace.resolve():
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "OpenClaw recognized a different target workspace.")
            actual_workspace = {
                item.path: item.data
                for item in _tree_items(workspace, "workspace", summarize_git=True)
                if item.data is not None
            }
            actual_agent = {
                item.path: item.data for item in _tree_items(agent.agent_dir, "agent") if item.data is not None
            }
            actual_sessions = {
                item.path: item.data
                for item in _tree_items(agent.agent_dir.parent / "sessions", "sessions")
                if item.data is not None
            }
            if actual_workspace != workspace_entries or actual_agent != agent_entries or actual_sessions != session_entries:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "OpenClaw target state does not match the native snapshot.",
                    details={
                        "workspace_expected": sorted(workspace_entries),
                        "workspace_actual": sorted(actual_workspace),
                        "agent_expected": sorted(agent_entries),
                        "agent_actual": sorted(actual_agent),
                        "sessions_expected": sorted(session_entries),
                        "sessions_actual": sorted(actual_sessions),
                    },
                )
        except Exception as error:
            if created_agent:
                self._rollback_created_target(name, workspace, error)
            raise
        layer_outcomes: list[dict[str, Any]] = []
        for layer in image.manifest["layers"]:
            if layer["kind"] == "native":
                action, reason = "preserved", "typed OpenClaw native state restored and validated"
            else:
                source = layer.get("source", {}).get("path", "")
                scope, separator, relative = source.partition("/")
                expected = {
                    "workspace": workspace_entries,
                    "agent": agent_entries,
                    "sessions": session_entries,
                }.get(scope, {})
                if separator and relative in expected and sha256_bytes(expected[relative]) == layer["digest"]:
                    action, reason = "preserved", "semantic layer invariant exists in restored native state"
                else:
                    action, reason = "unsupported", "semantic layer could not be reconciled to restored state"
            layer_outcomes.append({"id": layer["id"], "action": action, "reason": reason})
        source_report = image.json_entry("meta/source-report.json")
        outcomes: list[dict[str, Any]] = []
        restored_scopes = {
            "workspace": workspace_entries,
            "agent": agent_entries,
            "sessions": session_entries,
        }
        for source_item in source_report["outcomes"]:
            source = source_item.get("source")
            outcome: dict[str, Any] = {"id": source_item["id"], "source": source}
            source_action = source_item["action"]
            if source_action in {"redacted", "unsupported", "dropped_by_user"}:
                outcome.update(action=source_action, reason=source_item["reason"])
            elif source == f"registration/{image.manifest['image']['name']}":
                outcome.update(
                    action="transformed",
                    target=f"registration/{name}",
                    reason="agent registration recreated through the official OpenClaw CLI",
                )
            elif isinstance(source, str):
                scope, separator, relative = source.partition("/")
                restored = restored_scopes.get(scope, {})
                if separator and relative in restored:
                    outcome.update(action="preserved", reason="source item restored byte-for-byte")
                else:
                    outcome.update(action="unsupported", reason="source item could not be reconciled to target state")
            else:
                outcome.update(action="unsupported", reason="source item has no auditable locator")
            outcomes.append(outcome)
        return {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "restore",
            "adapter": {"id": self.id, "version": self.version},
            "target": f"openclaw:{name}",
            "target_workspace": str(workspace),
            "inventory_count": len(outcomes),
            "outcomes": outcomes,
            "loss_summary": _loss_summary(outcomes),
            "layer_inventory_count": len(layer_outcomes),
            "layer_outcomes": layer_outcomes,
            "layer_loss_summary": _loss_summary(layer_outcomes),
            "validated": True,
            "portability": "P1",
            "harness": {
                "id": "openclaw",
                "version": version,
                "tag": OPENCLAW_PIN.tag,
                "commit": OPENCLAW_PIN.commit,
            },
        }

    @staticmethod
    def _migration_target(source: str) -> str | None:
        if source in {"SOUL.md", "IDENTITY.md", "AGENTS.md", "TOOLS.md", "USER.md", "MEMORY.md"}:
            return source
        if source == "memories/MEMORY.md":
            return "MEMORY.md"
        if source == "memories/USER.md":
            return "USER.md"
        if source.startswith("skills/"):
            return source
        return None

    def migration_plan(self, image: ImageDocument, target: str) -> dict[str, Any]:
        version = self._require_pin()
        name = _agent_name(target, target=True)
        source_harness = image.manifest.get("runtime", {}).get("harness", {}).get("id")
        if source_harness != "hermes":
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "v0.1 semantic migration supports Hermes to OpenClaw only.")
        layers_by_source = {
            layer.get("source", {}).get("path"): layer
            for layer in image.manifest["layers"]
            if layer.get("source", {}).get("path")
        }
        source_report = image.json_entry("meta/source-report.json")
        outcomes: list[dict[str, Any]] = []
        for source_item in source_report["outcomes"]:
            source = source_item.get("source")
            outcome: dict[str, Any] = {"id": source_item["id"], "source": source}
            if source_item["action"] == "redacted":
                outcome.update(action="redacted", reason="source export already rejected secret/private material")
            elif source_item["action"] == "dropped_by_user":
                outcome.update(action="dropped_by_user", reason="source export excluded this item by explicit policy")
            elif source == "state.db":
                outcome.update(
                    action="unsupported",
                    reason="Hermes state.db remains preserved in the source image native layer and is not imported",
                )
            elif isinstance(source, str) and source.startswith("sessions/"):
                outcome.update(
                    action="unsupported",
                    reason="sessions remain private and are not semantically migrated in v0.1",
                )
            else:
                target_path = self._migration_target(str(source)) if source is not None else None
                layer = layers_by_source.get(source)
                if target_path is not None and layer is not None and layer["kind"] in {"identity", "skills", "memory", "workspace"}:
                    outcome.update(
                        action="transformed",
                        target=f"workspace/{target_path}",
                        layer_id=layer["id"],
                        reason="portable semantic layer mapped to the OpenClaw workspace contract",
                    )
                else:
                    outcome.update(
                        action="unsupported",
                        reason="no reliable Hermes-to-OpenClaw semantic mapping; item remains in the source image",
                    )
            outcomes.append(outcome)
        return {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "migrate-plan",
            "adapter": {"id": self.id, "version": self.version},
            "source_harness": source_harness,
            "source_image_digest": image.manifest["image"]["digest"],
            "target": f"openclaw:{name}",
            "target_harness": {"id": "openclaw", "version": version},
            "inventory_count": len(outcomes),
            "outcomes": outcomes,
            "loss_summary": _loss_summary(outcomes),
            "requires_confirmation": True,
            "dry_run": True,
            "portability": "P2-plan",
        }

    def semantic_migrate(self, image: ImageDocument, target: str) -> dict[str, Any]:
        plan = self.migration_plan(image, target)
        name, workspace = self._target_preflight(target)
        layers = {layer["id"]: layer for layer in image.manifest["layers"]}
        mapped: dict[str, bytes] = {}
        for outcome in plan["outcomes"]:
            if outcome["action"] != "transformed":
                continue
            layer = layers[outcome["layer_id"]]
            relative = outcome["target"].removeprefix("workspace/")
            data = image.entries[layer["path"]]
            filename = secret_filename_reason(relative)
            keys = structured_secret_findings(relative, layer["media_type"], data)
            if filename or keys:
                raise AgentImageError(
                    "E_SECRET_DETECTED",
                    f"Secret material cannot enter OpenClaw migration target: {relative}",
                    details={"filename": filename, "structured_keys": keys},
                )
            mapped[relative] = data
        created_agent = False
        try:
            agent = self.cli.add_agent(name, workspace)
            created_agent = True
            for relative, data in sorted(mapped.items()):
                target_path = agent.workspace / Path(*PurePosixPath(validate_archive_path(relative)).parts)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(data)
            provenance = {
                "protocol": "agent-image/v0.1",
                "operation": "semantic-migration",
                "source_image_digest": image.manifest["image"]["digest"],
                "source_harness": "hermes",
                "target_harness": "openclaw",
                "adapter": {"id": self.id, "version": self.version},
            }
            provenance_path = agent.workspace / ".agent-image" / "provenance.json"
            provenance_path.parent.mkdir(parents=True, exist_ok=True)
            provenance_path.write_bytes(canonical_json_bytes(provenance) + b"\n")
            recognized = self.cli.show_agent(name)
            if recognized.workspace.resolve() != workspace.resolve():
                raise AgentImageError("E_NATIVE_INCOMPATIBLE", "OpenClaw did not recognize the migration target.")
            for relative, expected in mapped.items():
                actual = (recognized.workspace / Path(*PurePosixPath(relative).parts)).read_bytes()
                if actual != expected:
                    raise AgentImageError(
                        "E_NATIVE_INCOMPATIBLE",
                        f"OpenClaw migration target failed validation: {relative}",
                    )
        except Exception as error:
            if created_agent:
                self._rollback_created_target(name, workspace, error)
            raise
        report = dict(plan)
        report.update(
            operation="migrate",
            target_workspace=str(workspace),
            requires_confirmation=False,
            dry_run=False,
            validated=True,
            portability="P2",
            provenance={
                "source_image_digest": image.manifest["image"]["digest"],
                "target_path": ".agent-image/provenance.json",
            },
        )
        return report
