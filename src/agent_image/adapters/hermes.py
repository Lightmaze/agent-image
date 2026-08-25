from __future__ import annotations

import gzip
import io
import os
import re
import subprocess
import tarfile
import tempfile
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
class HermesPin:
    version: str
    tag: str
    commit: str


HERMES_PIN = HermesPin(version="0.20.5", tag="v2026.8.19", commit="fcbd107")
HERMES_NATIVE_MEDIA_TYPE = "application/vnd.hermes-agent.profile.v2026.8.19+tar+gzip"
PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class HermesProfile:
    name: str
    path: Path


class HermesCLI(Protocol):
    def version(self) -> str: ...
    def show_profile(self, name: str) -> HermesProfile: ...
    def export_profile(self, name: str, output: Path) -> Path: ...
    def import_profile(self, archive: Path, name: str) -> HermesProfile: ...
    def delete_profile(self, name: str) -> None: ...


class SubprocessHermesCLI:
    def __init__(
        self,
        binary: str = "hermes",
        *,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.binary = binary
        self.environment = dict(environment or {})
        self.timeout_seconds = timeout_seconds

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(self.environment)
        env.setdefault("NO_COLOR", "1")
        env.setdefault("PYTHONUTF8", "1")
        return env

    def _run(self, arguments: list[str], *, error_code: str) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                [self.binary, *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._env(),
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as error:
            raise AgentImageError("E_ADAPTER_NOT_FOUND", f"Hermes executable was not found: {self.binary}") from error
        except subprocess.TimeoutExpired as error:
            raise AgentImageError(error_code, f"Hermes command timed out: {' '.join(arguments)}") from error
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip() or f"Hermes exited with {result.returncode}."
            raise AgentImageError(error_code, message, details={"command": arguments, "exit_code": result.returncode})
        return result

    def version(self) -> str:
        result = self._run(["--version"], error_code="E_SOURCE_UNSUPPORTED")
        match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)", f"{result.stdout}\n{result.stderr}")
        if not match:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Could not parse Hermes version output.")
        return match.group(1)

    def _fallback_profile_path(self, name: str) -> Path:
        configured = self._env().get("HERMES_HOME", "").strip()
        root = Path(configured).expanduser() if configured else Path.home() / ".hermes"
        return root if name == "default" else root / "profiles" / name

    def show_profile(self, name: str) -> HermesProfile:
        result = self._run(["profile", "show", name], error_code="E_SOURCE_NOT_FOUND")
        plain = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)
        match = re.search(r"^\s*Path:\s*(.+?)\s*$", plain, flags=re.MULTILINE)
        path = Path(match.group(1).strip()).expanduser() if match else self._fallback_profile_path(name)
        if not path.is_dir():
            fallback = self._fallback_profile_path(name)
            if fallback.is_dir():
                path = fallback
            else:
                raise AgentImageError("E_SOURCE_NOT_FOUND", f"Hermes profile path does not exist: {path}")
        return HermesProfile(name=name, path=path)

    def export_profile(self, name: str, output: Path) -> Path:
        if output.exists():
            raise AgentImageError("E_TARGET_EXISTS", f"Hermes export target already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        self._run(["profile", "export", name, "-o", str(output)], error_code="E_SOURCE_UNSUPPORTED")
        if not output.is_file():
            raise AgentImageError("E_SOURCE_UNSUPPORTED", f"Hermes did not create its declared export: {output}")
        return output

    def import_profile(self, archive: Path, name: str) -> HermesProfile:
        try:
            self.show_profile(name)
        except AgentImageError as error:
            if error.code != "E_SOURCE_NOT_FOUND":
                raise
        else:
            raise AgentImageError("E_TARGET_EXISTS", f"Hermes target already exists: {name}")
        self._run(["profile", "import", str(archive), "--name", name], error_code="E_NATIVE_INCOMPATIBLE")
        return self.show_profile(name)

    def delete_profile(self, name: str) -> None:
        self._run(["profile", "delete", name, "--yes"], error_code="E_NATIVE_INCOMPATIBLE")


@dataclass(frozen=True)
class _SourceFile:
    path: str
    data: bytes | None
    symlink: bool


def _profile_name(name: str, *, target: bool = False) -> str:
    normalized = name.strip().lower()
    if normalized == "default" and not target:
        return normalized
    if normalized == "default" or not PROFILE_NAME.fullmatch(normalized):
        code = "E_NATIVE_INCOMPATIBLE" if target else "E_SOURCE_NOT_FOUND"
        raise AgentImageError(code, f"Invalid Hermes profile name: {name!r}")
    return normalized


def _source_files(root: Path) -> dict[str, _SourceFile]:
    if not root.is_dir():
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"Hermes profile directory does not exist: {root}")
    result: dict[str, _SourceFile] = {}
    total_size = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if len(result) + 1 > MAX_ENTRIES:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Hermes source inventory exceeds Agent Image entry limits.")
        if path.is_symlink():
            result[relative] = _SourceFile(path=relative, data=None, symlink=True)
        elif path.is_file():
            try:
                size = path.stat().st_size
                if size < 0 or size > MAX_FILE_SIZE or total_size + size > MAX_TOTAL_SIZE:
                    raise AgentImageError(
                        "E_SOURCE_UNSUPPORTED",
                        f"Hermes source item exceeds Agent Image size limits: {relative}",
                    )
                total_size += size
                result[relative] = _SourceFile(path=relative, data=path.read_bytes(), symlink=False)
            except AgentImageError:
                raise
            except OSError as error:
                raise AgentImageError("E_SOURCE_UNSUPPORTED", f"Cannot read Hermes source item: {relative}") from error
    return result


def _profile_digest(root: Path) -> str:
    items = [
        {
            "path": item.path,
            "digest": sha256_bytes(item.data) if item.data is not None else "symlink",
        }
        for item in _source_files(root).values()
    ]
    return sha256_bytes(canonical_json_bytes(items))


def _safe_snapshot(archive_bytes: bytes) -> tuple[str, dict[str, bytes]]:
    entries: dict[str, bytes] = {}
    roots: set[str] = set()
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            for member in archive:
                normalized = member.name.replace("\\", "/")
                posix = PurePosixPath(normalized)
                windows = PureWindowsPath(member.name)
                if not normalized or posix.is_absolute() or windows.is_absolute() or windows.drive:
                    raise AgentImageError("E_UNSAFE_PATH", f"Unsafe Hermes archive path: {member.name}")
                parts = [part for part in posix.parts if part not in {"", "."}]
                if not parts or any(part == ".." for part in parts):
                    raise AgentImageError("E_UNSAFE_PATH", f"Unsafe Hermes archive path: {member.name}")
                roots.add(parts[0])
                if member.isdir():
                    continue
                if not member.isfile() or len(parts) < 2:
                    raise AgentImageError("E_UNSAFE_PATH", f"Unsupported Hermes archive member: {member.name}")
                relative = validate_archive_path("/".join(parts[1:]))
                if relative in entries:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Duplicate Hermes snapshot path: {relative}")
                if member.size < 0 or member.size > MAX_FILE_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Hermes snapshot item exceeds limits: {relative}")
                total += member.size
                if len(entries) + 1 > MAX_ENTRIES or total > MAX_TOTAL_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", "Hermes snapshot exceeds Agent Image safety limits.")
                stream = archive.extractfile(member)
                if stream is None:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Cannot read Hermes snapshot item: {relative}")
                data = stream.read(MAX_FILE_SIZE + 1)
                if len(data) != member.size:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Hermes snapshot size mismatch: {relative}")
                entries[relative] = data
    except AgentImageError:
        raise
    except (OSError, EOFError, tarfile.TarError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Cannot read Hermes profile archive: {error}") from error
    if len(roots) != 1:
        raise AgentImageError("E_IMAGE_CORRUPT", "Hermes profile archive must contain exactly one root directory.")
    return next(iter(roots)), entries


def _normalized_snapshot(root: str, entries: Mapping[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for relative in sorted(entries):
                data = entries[relative]
                info = tarfile.TarInfo(name=f"{root}/{relative}")
                info.size = len(data)
                info.mtime = 0
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


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
    }.get(suffix, "application/octet-stream")


def _logical_kind(path: str) -> str | None:
    name = PurePosixPath(path).name
    if path in {"SOUL.md", "system_prompt.md", "AGENTS.md", "CLAUDE.md", ".cursorrules"}:
        return "identity"
    if path.startswith("skills/"):
        return "skills"
    if path in {"MEMORY.md", "USER.md", "memories/MEMORY.md", "memories/USER.md"}:
        return "memory"
    if path.startswith(("memories/", "knowledge/", "preferences/")):
        return "memory"
    if path.startswith("sessions/"):
        return "experience"
    if name == "todo.json" or path.startswith(("workspace/", "plans/")):
        return "workspace"
    return None


def _layer_id(kind: str, path: str) -> str:
    return f"hermes-{kind}-{sha256_bytes(path.encode('utf-8'))[7:19]}"


class HermesAdapter:
    id = "org.agentimage.hermes"
    version = "0.1.0"
    locator_prefix = "hermes"

    def __init__(self, cli: HermesCLI | None = None) -> None:
        self.cli = cli or SubprocessHermesCLI()

    def _require_pin(self) -> str:
        actual = self.cli.version()
        if actual != HERMES_PIN.version:
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                f"Hermes {actual} is not the pinned compatibility target {HERMES_PIN.version}.",
                details={"actual": actual, "required": HERMES_PIN.version, "tag": HERMES_PIN.tag},
            )
        return actual

    def capabilities(self) -> dict[str, Any]:
        return {
            "archive": True,
            "native_restore": True,
            "semantic_migration": False,
            "portability_level": "P1",
            "pinned_harness": {"version": HERMES_PIN.version, "tag": HERMES_PIN.tag, "commit": HERMES_PIN.commit},
        }

    def profile_digest(self, name: str) -> str:
        profile = self.cli.show_profile(_profile_name(name))
        return _profile_digest(profile.path)

    def inspect_source(self, source: str) -> dict[str, Any]:
        version = self._require_pin()
        name = _profile_name(source)
        profile = self.cli.show_profile(name)
        files = _source_files(profile.path)
        return {
            "adapter": {"id": self.id, "version": self.version},
            "source_harness": {"id": "hermes", "version": version},
            "source": {"name": name, "path": str(profile.path.resolve()), "digest": _profile_digest(profile.path)},
            "inventory_count": len(files),
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
        name = _profile_name(source)
        profile = self.cli.show_profile(name)
        before = _profile_digest(profile.path)
        source_items = _source_files(profile.path)
        with tempfile.TemporaryDirectory(prefix="agent_image_hermes_export_") as temporary:
            official = Path(temporary) / f"{name}.tar.gz"
            self.cli.export_profile(name, official)
            official_bytes = official.read_bytes()
        after = _profile_digest(profile.path)
        if before != after:
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                "Hermes source profile changed during read-only export.",
                details={"before": before, "after": after},
            )
        snapshot_root, snapshot = _safe_snapshot(official_bytes)
        for path, data in snapshot.items():
            filename = secret_filename_reason(path)
            keys = structured_secret_findings(path, _media_type(path), data)
            if filename or keys:
                raise AgentImageError(
                    "E_SECRET_DETECTED",
                    f"Secret material survived the official Hermes export: {path}",
                    details={"filename": filename, "structured_keys": keys},
                )

        selected_snapshot = dict(snapshot)
        if not include_experience:
            selected_snapshot = {path: data for path, data in selected_snapshot.items() if not path.startswith("sessions/")}
        if not include_workspace:
            selected_snapshot = {
                path: data
                for path, data in selected_snapshot.items()
                if not (path == "todo.json" or path.startswith(("workspace/", "plans/")))
            }

        all_paths = sorted(set(source_items) | set(snapshot))
        outcomes: list[dict[str, Any]] = []
        for path in all_paths:
            source_item = source_items.get(path)
            snapshot_data = snapshot.get(path)
            item_id = f"source-{sha256_bytes(path.encode('utf-8'))[7:23]}"
            if source_item is not None and source_item.symlink:
                action, reason = "unsupported", "symlink is not admitted into Agent Image snapshots"
            elif secret_filename_reason(path):
                action, reason = "redacted", "credential filename excluded"
            elif snapshot_data is None:
                action, reason = "unsupported", "official Hermes export did not preserve this source item"
            elif policy == "public":
                action, reason = "redacted", "Hermes profile state is private by default"
            elif path not in selected_snapshot:
                action, reason = "dropped_by_user", "excluded by the explicit experience/workspace export policy"
            elif source_item is not None and source_item.data != snapshot_data:
                action, reason = "transformed", "official Hermes export transformed or scrubbed the item"
            else:
                action, reason = "preserved", "preserved in the typed native snapshot"
            outcome = {"id": item_id, "action": action, "reason": reason}
            if policy != "public":
                outcome["source"] = path
            outcomes.append(outcome)

        layers: list[dict[str, Any]] = []
        payloads: dict[str, bytes] = {}
        if policy == "private":
            for path, data in sorted(selected_snapshot.items()):
                kind = _logical_kind(path)
                if kind is None:
                    continue
                target = validate_archive_path(f"layers/{kind}/{path}")
                payloads[target] = data
                layers.append(
                    {
                        "id": _layer_id(kind, path),
                        "kind": kind,
                        "media_type": _media_type(path),
                        "path": target,
                        "digest": sha256_bytes(data),
                        "size": len(data),
                        "privacy": "private",
                        "portability": "portable",
                        "source": {"path": path, "origin": f"hermes:{name}", "reason": "recognized Hermes semantic surface"},
                    }
                )
            native = _normalized_snapshot(snapshot_root, selected_snapshot)
            native_path = "layers/native/hermes-profile.tar.gz"
            payloads[native_path] = native
            layers.append(
                {
                    "id": "hermes-native-profile",
                    "kind": "native",
                    "media_type": HERMES_NATIVE_MEDIA_TYPE,
                    "path": native_path,
                    "digest": sha256_bytes(native),
                    "size": len(native),
                    "privacy": "private",
                    "portability": "opaque",
                    "source": {"origin": f"hermes:{name}", "reason": "normalized official Hermes profile export"},
                }
            )
        layers.sort(key=lambda layer: layer["path"])
        manifest: dict[str, Any] = {
            "spec": "agent-image/v0.1",
            "image": {
                "name": name,
                "version": "0.1.0",
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "digest": layer_root_digest(layers),
                "description": f"Hermes profile checkpoint exported through {self.id}",
            },
            "runtime": {
                "harness": {"id": "hermes", "version": version},
                "adapter": {"id": self.id, "version": self.version},
            },
            "layers": layers,
            "privacy": {"default": "private", "public_build": policy == "public", "unresolved_items": 0},
            "provenance": {
                "source_harness": "hermes",
                "source_adapter": self.id,
                "export_tool_version": __version__,
                "source_uri": f"hermes:{name}",
            },
            "extensions": {
                "org.agentimage.hermes.contract": {
                    "version": HERMES_PIN.version,
                    "tag": HERMES_PIN.tag,
                    "commit": HERMES_PIN.commit,
                    "source_profile_digest": before,
                }
            },
        }
        report = {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "build",
            "adapter": {"id": self.id, "version": self.version},
            "inventory_count": len(outcomes),
            "outcomes": outcomes,
        }
        return AdapterExport(manifest=manifest, payloads=payloads, source_report=report)

    def native_restore(self, image: ImageDocument, target: str) -> dict[str, Any]:
        version = self._require_pin()
        name = _profile_name(target, target=True)
        runtime = image.manifest.get("runtime", {})
        harness = runtime.get("harness", {}) if isinstance(runtime, dict) else {}
        if harness != {"id": "hermes", "version": version}:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Image is not compatible with the pinned Hermes runtime.")
        try:
            self.cli.show_profile(name)
        except AgentImageError as error:
            if error.code != "E_SOURCE_NOT_FOUND":
                raise
        else:
            raise AgentImageError("E_TARGET_EXISTS", f"Hermes target already exists: {name}")
        native_layers = [
            layer
            for layer in image.manifest["layers"]
            if layer["kind"] == "native" and layer["media_type"] == HERMES_NATIVE_MEDIA_TYPE
        ]
        if len(native_layers) != 1:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Hermes P1 requires exactly one pinned native profile layer.")
        native_layer = native_layers[0]
        native = image.entries[native_layer["path"]]
        _, expected = _safe_snapshot(native)
        with tempfile.TemporaryDirectory(prefix="agent_image_hermes_restore_") as temporary:
            archive = Path(temporary) / "profile.tar.gz"
            archive.write_bytes(native)
            created = False
            try:
                profile = self.cli.import_profile(archive, name)
                created = True
                self.cli.show_profile(name)
                actual_items = _source_files(profile.path)
                actual = {path: item.data for path, item in actual_items.items() if not item.symlink and item.data is not None}
                if actual != expected:
                    raise AgentImageError(
                        "E_NATIVE_INCOMPATIBLE",
                        "Hermes target state does not match the native snapshot after import.",
                        details={"expected_paths": sorted(expected), "actual_paths": sorted(actual)},
                    )
            except Exception:
                if created:
                    try:
                        self.cli.delete_profile(name)
                    except Exception:
                        pass
                raise
        outcomes: list[dict[str, Any]] = []
        for layer in image.manifest["layers"]:
            if layer["kind"] == "native":
                action, reason = "preserved", "official native profile imported and validated"
            else:
                source = layer.get("source", {}).get("path")
                if source and source in expected and sha256_bytes(expected[source]) == layer["digest"]:
                    action, reason = "preserved", "semantic layer invariant present in restored native profile"
                else:
                    action, reason = "unsupported", "semantic layer could not be reconciled to restored native state"
            outcomes.append({"id": layer["id"], "action": action, "reason": reason})
        return {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "restore",
            "adapter": {"id": self.id, "version": self.version},
            "target": name,
            "inventory_count": len(outcomes),
            "outcomes": outcomes,
            "validated": True,
            "portability": "P1",
            "harness": {"id": "hermes", "version": version, "tag": HERMES_PIN.tag, "commit": HERMES_PIN.commit},
        }
