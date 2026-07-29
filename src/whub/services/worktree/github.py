"""GitHub CLI helpers for worktree lifecycle operations."""

from __future__ import annotations

from pathlib import Path
import subprocess

from whub.services.errors import ServiceError


def run_gh(worktree: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run GitHub CLI in WORKTREE and convert invocation failures."""
    try:
        return subprocess.run(
            ["gh", *arguments],
            cwd=worktree,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ServiceError(f"gh invocation failed: {error}") from error
