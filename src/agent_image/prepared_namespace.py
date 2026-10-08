"""Filesystem namespace ownership for prepared Agent Image build publication.

The caller controls a trusted parent directory. Exclusive mkdir and hardlink
publication prevent collisions with cooperating publishers on the same
filesystem. This module does not claim hostile-parent sandboxing, remote
filesystem semantics, or directory-entry crash durability.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from agent_image.errors import AgentImageError


def claim_new_prepared_workspace(workspace: Path) -> None:
    """Acquire a fresh workspace name without adopting existing directories."""
    try:
        workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
    except FileExistsError as error:
        raise AgentImageError(
            "E_TARGET_EXISTS",
            f"Prepared workspace already exists: {workspace}",
        ) from error
    except OSError as error:
        raise AgentImageError(
            "E_IMAGE_CORRUPT",
            f"Could not exclusively claim prepared workspace: {error}",
        ) from error


def publish_prepared_control_bytes_exclusive(path: Path, payload: bytes) -> None:
    """Stage a complete receipt and bind its final name only if absent.

    The hard-link operation is the no-clobber linearization point.
    Unsupported filesystems fail closed; no truncate/open or replace fallback.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    try:
        fd, name = tempfile.mkstemp(prefix=f".{path.name}.staged-", dir=path.parent)
        staged = Path(name)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(staged, path, follow_symlinks=False)
        except FileExistsError as error:
            raise AgentImageError("E_TARGET_EXISTS", f"Prepared receipt already exists: {path}") from error
        except OSError as error:
            raise AgentImageError(
                "E_IMAGE_CORRUPT",
                f"Cannot commit prepared receipt without clobber: {error}",
            ) from error
    except AgentImageError:
        raise
    except OSError as error:
        raise AgentImageError("E_IMAGE_CORRUPT", f"Could not stage prepared receipt: {error}") from error
    finally:
        if staged is not None:
            try:
                staged.unlink(missing_ok=True)
            except OSError:
                # A leftover private stage does not authorize removing its final link.
                pass
