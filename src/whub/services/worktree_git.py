"""Git process helpers shared by worktree services."""

from __future__ import annotations

from pathlib import Path
import subprocess

from whub.services.errors import ServiceError


def run_git(parent: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run Git for PARENT and convert invocation failures to service errors."""
    try:
        return subprocess.run(
            ["git", "-C", str(parent), *arguments],
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ServiceError(f"git invocation failed: {error}") from error


def process_detail(result: subprocess.CompletedProcess[str]) -> str:
    """Return a concise failure detail for a completed Git process."""
    return result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
