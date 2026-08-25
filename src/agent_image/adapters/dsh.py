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
class DshPin:
    version: str
    node: str
    npm: str


DSH_PIN = DshPin(version="0.1.0-rc.6", node="24.15.0", npm="11.12.1")
DSH_NATIVE_MEDIA_TYPE = "application/vnd.deepseek-harness.profile.v0.1.0-rc.6+tar+gzip"
PROFILE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class DshProfile:
    name: str
    path: Path


class DshCLI(Protocol):
    def version(self) -> str: ...
    def home(self) -> Path: ...
    def show_profile(self, name: str) -> DshProfile: ...
    def target_profile(self, name: str) -> Path: ...
    def dump_config(self, name: str) -> bytes: ...
    def delete_profile(self, name: str) -> None: ...


class SubprocessDshCLI:
    def __init__(
        self,
        binary: str = "dsh",
        *,
        node_binary: str | None = None,
        dsh_home: Path | None = None,
        environment: Mapping[str, str] | None = None,
        timeout_seconds: int = 180,
    ) -> None:
        self.binary = binary
        self.node_binary = node_binary
        self.dsh_home = dsh_home
        self.environment = dict(environment or {})
        self.timeout_seconds = timeout_seconds

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(self.environment)
        if self.dsh_home is not None:
            env["DSH_HOME"] = str(self.dsh_home.expanduser().resolve())
        env.setdefault("NO_COLOR", "1")
        env.setdefault("DSH_TELEMETRY_DISABLED", "1")
        return env

    def _command(self, arguments: list[str]) -> list[str]:
        if self.node_binary is None:
            return [self.binary, *arguments]
        binary = Path(self.binary).expanduser().resolve()
        if binary.suffix.lower() in {".js", ".mjs"}:
            script = binary
        elif binary.suffix.lower() in {".cmd", ".ps1"}:
            script = binary.parent / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
        else:
            raise AgentImageError(
                "E_ADAPTER_NOT_FOUND",
                "Explicit DSH Node execution requires dsh bin.js or an npm dsh shim.",
                details={"binary": str(binary)},
            )
        if not script.is_file():
            raise AgentImageError("E_ADAPTER_NOT_FOUND", f"DSH module entry point was not found: {script}")
        return [self.node_binary, str(script), *arguments]

    def _run(self, arguments: list[str], *, error_code: str) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                self._command(arguments),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self._env(),
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as error:
            raise AgentImageError("E_ADAPTER_NOT_FOUND", f"DSH executable was not found: {self.binary}") from error
        except subprocess.TimeoutExpired as error:
            raise AgentImageError(error_code, f"DSH command timed out: {' '.join(arguments)}") from error
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip() or f"DSH exited with {result.returncode}."
            raise AgentImageError(
                error_code,
                message,
                details={"command": arguments, "exit_code": result.returncode},
            )
        return result

    def version(self) -> str:
        result = self._run(["--version"], error_code="E_SOURCE_UNSUPPORTED")
        match = re.search(r"(?<![\w.-])(\d+\.\d+\.\d+-rc\.\d+)(?![\w.-])", result.stdout)
        if not match:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "Could not parse DSH version output.")
        return match.group(1)

    def home(self) -> Path:
        configured = self._env().get("DSH_HOME", "").strip()
        return (Path(configured).expanduser() if configured else Path.home() / ".dsh").resolve()

    def target_profile(self, name: str) -> Path:
        return (self.home() / "profiles" / name).resolve()

    def show_profile(self, name: str) -> DshProfile:
        path = self.target_profile(name)
        if not path.is_dir() or not (path / "package.json").is_file():
            raise AgentImageError("E_SOURCE_NOT_FOUND", f"DSH profile does not exist: {name}")
        return DshProfile(name=name, path=path)

    def dump_config(self, name: str) -> bytes:
        self.show_profile(name)
        result = self._run(
            ["--profile", name, "--dump-config"],
            error_code="E_NATIVE_INCOMPATIBLE",
        )
        if not result.stdout.strip():
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH returned an empty composed configuration.")
        return result.stdout.encode("utf-8")

    def delete_profile(self, name: str) -> None:
        profile = self.target_profile(name)
        profiles_root = (self.home() / "profiles").resolve()
        if profile.parent.resolve() != profiles_root or not profile.is_dir():
            raise AgentImageError("E_ROLLBACK_FAILED", f"Refusing to remove unexpected DSH profile path: {profile}")
        shutil.rmtree(profile)


@dataclass(frozen=True)
class _SourceItem:
    source: str
    data: bytes | None
    item_type: str


def _profile_name(name: str, *, target: bool = False) -> str:
    normalized = name.strip().lower()
    if not PROFILE_NAME.fullmatch(normalized):
        code = "E_NATIVE_INCOMPATIBLE" if target else "E_SOURCE_NOT_FOUND"
        raise AgentImageError(code, f"Invalid DSH profile name: {name!r}")
    return normalized


def _media_type(path: str) -> str:
    suffix = PurePosixPath(path).suffix.casefold()
    if suffix == ".json":
        return "application/json"
    if suffix in {".yaml", ".yml"}:
        return "application/yaml"
    if suffix in {".md", ".txt"}:
        return "text/plain"
    return "application/octet-stream"


def _profile_manifest(data: bytes) -> tuple[list[str], dict[str, str]]:
    try:
        value = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH package.json must be valid UTF-8 JSON.") from error
    profile = value.get("dsh", {}).get("profile") if isinstance(value, dict) else None
    bundles = profile.get("bundles") if isinstance(profile, dict) else None
    dependencies = value.get("dependencies", {}) if isinstance(value, dict) else None
    if not isinstance(bundles, list) or not bundles or not all(isinstance(item, str) and item for item in bundles):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH package.json must declare ordered dsh.profile.bundles.")
    if not isinstance(dependencies, dict) or not all(
        isinstance(name, str) and name and isinstance(version, str) and version
        for name, version in dependencies.items()
    ):
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH dependencies must be a string-to-string object.")
    return list(bundles), dict(sorted(dependencies.items()))


def _source_items(root: Path) -> dict[str, _SourceItem]:
    if not root.is_dir():
        raise AgentImageError("E_SOURCE_NOT_FOUND", f"DSH profile directory does not exist: {root}")
    items: dict[str, _SourceItem] = {}
    total_size = 0
    saw_node_modules = False
    for path in sorted(root.rglob("*")):
        relative_path = path.relative_to(root)
        relative = relative_path.as_posix()
        if relative_path.parts and relative_path.parts[0] == "node_modules":
            if not saw_node_modules:
                items["profile/node_modules/"] = _SourceItem(
                    source="profile/node_modules/", data=None, item_type="dependency-directory"
                )
                saw_node_modules = True
            continue
        if path.is_symlink():
            items[f"profile/{relative}"] = _SourceItem(
                source=f"profile/{relative}", data=None, item_type="symlink"
            )
            continue
        if not path.is_file():
            continue
        if len(items) + 1 > MAX_ENTRIES:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH source inventory exceeds Agent Image limits.")
        size = path.stat().st_size
        if size < 0 or size > MAX_FILE_SIZE or total_size + size > MAX_TOTAL_SIZE:
            raise AgentImageError("E_SOURCE_UNSUPPORTED", f"DSH source item exceeds size limits: {relative}")
        total_size += size
        items[f"profile/{relative}"] = _SourceItem(
            source=f"profile/{relative}", data=path.read_bytes(), item_type="file"
        )
    package = items.get("profile/package.json")
    patch = items.get("profile/cordis.patch.yml")
    if package is None or package.data is None or patch is None or patch.data is None:
        raise AgentImageError("E_SOURCE_UNSUPPORTED", "DSH profile requires package.json and cordis.patch.yml.")
    bundles, dependencies = _profile_manifest(package.data)
    for index, bundle in enumerate(bundles):
        source = f"manifest/bundles/{index:04d}/{bundle}"
        items[source] = _SourceItem(source=source, data=bundle.encode("utf-8"), item_type="bundle")
    for dependency, version in dependencies.items():
        source = f"manifest/dependencies/{dependency}"
        items[source] = _SourceItem(source=source, data=version.encode("utf-8"), item_type="dependency")
    return items


def _inventory_digest(items: Mapping[str, _SourceItem]) -> str:
    rows = [
        {
            "source": source,
            "type": item.item_type,
            "digest": sha256_bytes(item.data) if item.data is not None else None,
        }
        for source, item in sorted(items.items())
    ]
    return sha256_bytes(canonical_json_bytes(rows))


def _loss_summary(outcomes: list[dict[str, Any]]) -> dict[str, int]:
    keys = ("preserved", "transformed", "redacted", "unsupported", "dropped_by_user")
    return {key: sum(1 for item in outcomes if item["action"] == key) for key in keys}


def _tar_bytes(entries: Mapping[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for path, data in sorted(entries.items()):
                safe = validate_archive_path(path)
                info = tarfile.TarInfo(safe)
                info.size = len(data)
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


def _read_native(data: bytes) -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) > MAX_ENTRIES:
                raise AgentImageError("E_IMAGE_CORRUPT", "DSH native layer exceeds entry limits.")
            for member in members:
                path = validate_archive_path(member.name)
                if member.issym() or member.islnk() or not member.isfile():
                    raise AgentImageError("E_IMAGE_CORRUPT", f"DSH native layer contains a non-file: {path}")
                if member.size < 0 or member.size > MAX_FILE_SIZE or total + member.size > MAX_TOTAL_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"DSH native item exceeds size limits: {path}")
                if path in entries:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Duplicate DSH native path: {path}")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Unreadable DSH native path: {path}")
                payload = extracted.read()
                if len(payload) != member.size:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Truncated DSH native path: {path}")
                total += len(payload)
                entries[path] = payload
    except AgentImageError:
        raise
    except (tarfile.TarError, OSError, EOFError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", "Invalid DSH native archive.") from error
    return entries


def _write_profile(root: Path, entries: Mapping[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=False)
    for relative, data in sorted(entries.items()):
        safe = validate_archive_path(relative)
        if PureWindowsPath(safe).is_absolute():
            raise AgentImageError("E_IMAGE_CORRUPT", f"Absolute DSH target path: {safe}")
        target = root / Path(*PurePosixPath(safe).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


class DshAdapter:
    id = "org.agentimage.dsh"
    version = "0.1.0"
    locator_prefix = "dsh"

    def __init__(self, cli: DshCLI | None = None) -> None:
        self.cli = cli or SubprocessDshCLI()

    def _require_pin(self) -> str:
        version = self.cli.version()
        if version != DSH_PIN.version:
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                f"DSH version {version} is not the pinned contract {DSH_PIN.version}.",
            )
        return version

    def capabilities(self) -> dict[str, Any]:
        return {
            "archive": True,
            "native_restore": True,
            "semantic_migration": False,
            "portability_level": "P1",
            "pinned_harness": {
                "version": DSH_PIN.version,
                "node": DSH_PIN.node,
                "npm": DSH_PIN.npm,
            },
        }

    def inspect_source(self, source: str) -> dict[str, Any]:
        version = self._require_pin()
        name = _profile_name(source)
        profile = self.cli.show_profile(name)
        items = _source_items(profile.path)
        return {
            "adapter": {"id": self.id, "version": self.version},
            "source_harness": {"id": "dsh", "version": version},
            "source": {
                "name": name,
                "path": str(profile.path.resolve()),
                "digest": _inventory_digest(items),
            },
            "inventory_count": len(items),
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
        version = self._require_pin()
        name = _profile_name(source)
        profile = self.cli.show_profile(name)
        before_items = _source_items(profile.path)
        before = _inventory_digest(before_items)
        file_entries: dict[str, bytes] = {}
        for item in before_items.values():
            if item.data is None or item.item_type not in {"file", "bundle", "dependency"}:
                continue
            filename = secret_filename_reason(item.source)
            keys = structured_secret_findings(item.source, _media_type(item.source), item.data)
            if filename or keys:
                raise AgentImageError(
                    "E_SECRET_DETECTED",
                    f"Secret material cannot enter a DSH image: {item.source}",
                    details={"filename": filename, "structured_keys": keys},
                )
            if item.item_type == "file":
                file_entries[item.source.removeprefix("profile/")] = item.data
        dump_config = self.cli.dump_config(name)
        after_items = _source_items(profile.path)
        after = _inventory_digest(after_items)
        if before != after:
            raise AgentImageError(
                "E_SOURCE_UNSUPPORTED",
                "DSH source profile changed during read-only export.",
                details={"before": before, "after": after},
            )
        package_data = file_entries["package.json"]
        bundles, dependencies = _profile_manifest(package_data)
        outcomes: list[dict[str, Any]] = []
        for source_path, item in sorted(before_items.items()):
            item_id = f"source-{sha256_bytes(source_path.encode('utf-8'))[7:23]}"
            if item.item_type in {"symlink", "dependency-directory"}:
                action, reason = "unsupported", "dependency directories and symlinks are not archived"
            elif policy == "public":
                action, reason = "redacted", "DSH composition is private by default"
            else:
                action, reason = "preserved", "preserved in the typed DSH native composition"
            outcome = {"id": item_id, "source": source_path, "action": action, "reason": reason}
            outcomes.append(outcome)
        composition_id = f"source-{sha256_bytes(b'composition/dump-config')[7:23]}"
        outcomes.append(
            {
                "id": composition_id,
                "source": "composition/dump-config",
                "action": "redacted" if policy == "public" else "transformed",
                "reason": "official --dump-config composition derived from the ordered profile",
            }
        )
        layers: list[dict[str, Any]] = []
        payloads: dict[str, bytes] = {}
        if policy == "private":
            native_entries = {f"profile/{path}": data for path, data in file_entries.items()}
            native_entries.update(
                {
                    "meta/profile.json": canonical_json_bytes(
                        {"source_name": name, "bundles": bundles, "dependencies": dependencies}
                    )
                    + b"\n",
                    "meta/dump-config.yml": dump_config,
                }
            )
            native = _tar_bytes(native_entries)
            native_path = "layers/native/dsh-profile.tar.gz"
            payloads[native_path] = native
            layers.append(
                {
                    "id": "dsh-native-profile",
                    "kind": "native",
                    "media_type": DSH_NATIVE_MEDIA_TYPE,
                    "path": native_path,
                    "digest": sha256_bytes(native),
                    "size": len(native),
                    "privacy": "private",
                    "portability": "opaque",
                    "source": {
                        "origin": f"dsh:{name}",
                        "reason": "ordered bundles, dependencies, patch files, and official config dump",
                    },
                }
            )
        manifest: dict[str, Any] = {
            "spec": "agent-image/v0.1",
            "image": {
                "name": name,
                "version": "0.1.0",
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "digest": layer_root_digest(layers),
                "description": f"DSH profile composition exported through {self.id}",
            },
            "runtime": {
                "harness": {"id": "dsh", "version": version},
                "adapter": {"id": self.id, "version": self.version},
            },
            "layers": layers,
            "privacy": {"default": "private", "public_build": policy == "public", "unresolved_items": 0},
            "provenance": {
                "source_harness": "dsh",
                "source_adapter": self.id,
                "export_tool_version": __version__,
                "source_uri": f"dsh:{name}",
            },
            "extensions": {
                "org.agentimage.dsh.contract": {
                    "version": DSH_PIN.version,
                    "source_profile_digest": before,
                    "dump_config_digest": sha256_bytes(dump_config),
                    "bundle_order": bundles,
                    "dependencies": dependencies,
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
        name = _profile_name(target, target=True)
        path = self.cli.target_profile(name)
        if path.exists():
            raise AgentImageError("E_TARGET_EXISTS", f"DSH target profile already exists: {name}")
        profiles_root = (self.cli.home() / "profiles").resolve()
        if path.parent.resolve() != profiles_root:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", f"DSH target escaped profiles root: {path}")
        return name, path

    def _rollback(self, name: str, path: Path, original: Exception) -> None:
        errors: list[str] = []
        if path.exists():
            try:
                self.cli.delete_profile(name)
            except Exception as error:
                errors.append(str(error))
        if path.exists():
            errors.append("target profile directory still exists")
        if errors:
            raise AgentImageError(
                "E_ROLLBACK_FAILED",
                f"DSH target rollback was incomplete: {name}",
                details={"original_error": str(original), "residuals": errors},
            ) from original

    def native_restore(self, image: ImageDocument, target: str) -> dict[str, Any]:
        version = self._require_pin()
        name, profile_path = self._target_preflight(target)
        harness = image.manifest.get("runtime", {}).get("harness", {})
        if harness != {"id": "dsh", "version": version}:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "Image is not compatible with pinned DSH.")
        native_layers = [
            layer
            for layer in image.manifest["layers"]
            if layer["kind"] == "native" and layer["media_type"] == DSH_NATIVE_MEDIA_TYPE
        ]
        if len(native_layers) != 1:
            raise AgentImageError("E_NATIVE_INCOMPATIBLE", "DSH P1 requires one pinned native layer.")
        entries = _read_native(image.entries[native_layers[0]["path"]])
        try:
            metadata = json.loads(entries.pop("meta/profile.json").decode("utf-8"))
            expected_dump = entries.pop("meta/dump-config.yml")
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AgentImageError("E_IMAGE_CORRUPT", "DSH native metadata is missing or invalid.") from error
        profile_entries = {
            path.removeprefix("profile/"): data for path, data in entries.items() if path.startswith("profile/")
        }
        if len(profile_entries) != len(entries):
            raise AgentImageError("E_IMAGE_CORRUPT", "DSH native layer contains an unknown root entry.")
        bundles, dependencies = _profile_manifest(profile_entries.get("package.json", b""))
        if metadata.get("bundles") != bundles or metadata.get("dependencies") != dependencies:
            raise AgentImageError("E_IMAGE_CORRUPT", "DSH native manifest metadata does not match package.json.")
        created = False
        try:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            _write_profile(profile_path, profile_entries)
            created = True
            recognized = self.cli.show_profile(name)
            actual_dump = self.cli.dump_config(name)
            actual_items = _source_items(recognized.path)
            actual_files = {
                item.source.removeprefix("profile/"): item.data
                for item in actual_items.values()
                if item.item_type == "file" and item.data is not None
            }
            if actual_files != profile_entries:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH target profile files do not match the native snapshot.",
                    details={
                        "expected": sorted(profile_entries),
                        "actual": sorted(actual_files),
                    },
                )
            if actual_dump != expected_dump:
                raise AgentImageError(
                    "E_NATIVE_INCOMPATIBLE",
                    "DSH --dump-config differs after restore; dependency or composition drift detected.",
                    details={
                        "expected_digest": sha256_bytes(expected_dump),
                        "actual_digest": sha256_bytes(actual_dump),
                    },
                )
        except Exception as error:
            if created or profile_path.exists():
                self._rollback(name, profile_path, error)
            raise
        source_report = image.json_entry("meta/source-report.json")
        outcomes: list[dict[str, Any]] = []
        for source_item in source_report["outcomes"]:
            source_path = source_item.get("source")
            outcome: dict[str, Any] = {"id": source_item["id"], "source": source_path}
            if source_item["action"] in {"redacted", "unsupported", "dropped_by_user"}:
                outcome.update(action=source_item["action"], reason=source_item["reason"])
            elif source_path == "composition/dump-config":
                outcome.update(action="preserved", reason="official composed config digest matches after restore")
            elif isinstance(source_path, str) and source_path.startswith("profile/"):
                relative = source_path.removeprefix("profile/")
                if relative in profile_entries:
                    outcome.update(action="preserved", reason="profile file restored byte-for-byte")
                else:
                    outcome.update(action="unsupported", reason="profile item was not present in the native snapshot")
            elif isinstance(source_path, str) and source_path.startswith("manifest/bundles/"):
                index_text, _, bundle = source_path.removeprefix("manifest/bundles/").partition("/")
                index = int(index_text) if index_text.isdigit() else -1
                if 0 <= index < len(bundles) and bundles[index] == bundle:
                    outcome.update(action="preserved", reason="bundle position retained")
                else:
                    outcome.update(action="unsupported", reason="bundle order could not be reconciled")
            elif isinstance(source_path, str) and source_path.startswith("manifest/dependencies/"):
                dependency = source_path.removeprefix("manifest/dependencies/")
                if dependency in dependencies:
                    outcome.update(action="preserved", reason="dependency metadata retained")
                else:
                    outcome.update(action="unsupported", reason="dependency metadata could not be reconciled")
            else:
                outcome.update(action="unsupported", reason="source item has no DSH restore mapping")
            outcomes.append(outcome)
        layer_outcomes = [
            {
                "id": native_layers[0]["id"],
                "action": "preserved",
                "reason": "typed DSH native composition restored and --dump-config validated",
            }
        ]
        return {
            "report_version": "agent-image-operation-report/v0.1",
            "operation": "restore",
            "adapter": {"id": self.id, "version": self.version},
            "target": f"dsh:{name}",
            "target_profile": str(profile_path),
            "inventory_count": len(outcomes),
            "outcomes": outcomes,
            "loss_summary": _loss_summary(outcomes),
            "layer_inventory_count": 1,
            "layer_outcomes": layer_outcomes,
            "layer_loss_summary": _loss_summary(layer_outcomes),
            "bundle_order": bundles,
            "dependencies": dependencies,
            "dump_config_digest": sha256_bytes(expected_dump),
            "validated": True,
            "portability": "P1",
            "harness": {"id": "dsh", "version": version},
        }
