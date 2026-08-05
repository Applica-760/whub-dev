"""GitHub CLI helpers for worktree lifecycle operations."""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from whub.core.remote import run_ssh_command
from whub.models import Host
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


def run_remote_gh(
    host: Host, worktree: str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run GitHub CLI in a remote worktree through SSH."""
    command = f"cd {shlex.quote(worktree)} && gh {shlex.join(arguments)}"
    try:
        return run_ssh_command(host, command)
    except OSError as error:
        raise ServiceError(f"remote gh invocation failed: {error}") from error


def run_worktree_gh(
    host: Host | None, worktree: Path | str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run GitHub CLI at a resolved local or remote worktree location."""
    if host is None:
        assert isinstance(worktree, Path)
        return run_gh(worktree, *arguments)
    assert isinstance(worktree, str)
    return run_remote_gh(host, worktree, *arguments)
