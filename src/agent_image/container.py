from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path
from typing import Mapping

from agent_image.errors import AgentImageError
from agent_image.paths import validate_archive_path


MAX_ENTRIES = 10_000
MAX_FILE_SIZE = 256 * 1024 * 1024
MAX_TOTAL_SIZE = 1024 * 1024 * 1024


def pack_entries(
    entries: Mapping[str, bytes],
    output: Path,
    *,
    validate_paths: bool = True,
) -> None:
    if output.exists():
        raise AgentImageError("E_TARGET_EXISTS", f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                    for name in sorted(entries):
                        if validate_paths:
                            validate_archive_path(name)
                        data = entries[name]
                        if not isinstance(data, bytes):
                            raise AgentImageError("E_IMAGE_CORRUPT", f"Entry {name!r} is not bytes.")
                        info = tarfile.TarInfo(name=name)
                        info.size = len(data)
                        info.mtime = 0
                        info.mode = 0o644
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        archive.addfile(info, io.BytesIO(data))
    except AgentImageError:
        output.unlink(missing_ok=True)
        raise
    except OSError as error:
        output.unlink(missing_ok=True)
        raise AgentImageError("E_IMAGE_CORRUPT", f"Could not pack image: {error}") from error


def read_entries(image: Path) -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    total_size = 0
    try:
        with tarfile.open(image, mode="r:gz") as archive:
            for member in archive:
                validate_archive_path(member.name)
                if member.name in entries:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Duplicate archive path: {member.name}")
                if not member.isfile():
                    raise AgentImageError("E_UNSAFE_PATH", f"Only regular files are allowed: {member.name}")
                if member.size < 0 or member.size > MAX_FILE_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Archive entry size is outside limits: {member.name}")
                total_size += member.size
                if len(entries) + 1 > MAX_ENTRIES or total_size > MAX_TOTAL_SIZE:
                    raise AgentImageError("E_IMAGE_CORRUPT", "Archive exceeds v0.1 safety limits.")
                stream = archive.extractfile(member)
                if stream is None:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Cannot read archive entry: {member.name}")
                data = stream.read(MAX_FILE_SIZE + 1)
                if len(data) != member.size:
                    raise AgentImageError("E_IMAGE_CORRUPT", f"Archive entry size mismatch: {member.name}")
                entries[member.name] = data
    except AgentImageError:
        raise
    except (OSError, EOFError, tarfile.TarError) as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Cannot read Agent Image: {error}") from error
    return entries

