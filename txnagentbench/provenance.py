"""Shared Week-1 source and dependency provenance, reused by Gate 1B."""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from pydantic import JsonValue


def source_provenance(root: Path) -> dict[str, JsonValue]:
    source_commit = os.environ.get("AGENTTXN_SOURCE_COMMIT", "unavailable")
    source_dirty: bool | None = None
    if shutil.which("git"):
        command = ["git", "-c", f"safe.directory={root.as_posix()}"]
        revision = subprocess.run(
            [*command, "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        source_commit = revision.stdout.strip() or source_commit
        status = subprocess.run(
            [*command, "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        source_dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
    source_digest = hashlib.sha256()
    for package in ("agenttxn", "services", "txnagentbench", "baselines", "experiments"):
        for source in sorted((root / package).rglob("*")):
            if source.suffix in {".py", ".sql"}:
                source_digest.update(source.relative_to(root).as_posix().encode() + b"\0")
                source_digest.update(source.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return {
        "source_commit": source_commit,
        "source_dirty": source_dirty,
        "source_tree_sha256": source_digest.hexdigest(),
        "lockfile_sha256": (
            hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
            if (root / "uv.lock").exists()
            else "unavailable"
        ),
    }
