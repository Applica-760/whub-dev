"""Git process helpers shared by worktree services."""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from whub.core.remote import run_ssh_command
from whub.models import Host
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


def run_remote_git(
    host: Host, directory: str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run Git in DIRECTORY on HOST through the established SSH transport."""
    command = f"git -C {shlex.quote(directory)} {shlex.join(arguments)}"
    try:
        return run_ssh_command(host, command)
    except OSError as error:
        raise ServiceError(f"remote git invocation failed: {error}") from error


def run_worktree_git(
    host: Host | None, directory: Path | str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run Git at a resolved local or remote worktree location."""
    if host is None:
        assert isinstance(directory, Path)
        return run_git(directory, *arguments)
    assert isinstance(directory, str)
    return run_remote_git(host, directory, *arguments)


def process_detail(result: subprocess.CompletedProcess[str]) -> str:
    """Return a concise failure detail for a completed Git process."""
    return (
        result.stderr.strip()
        or result.stdout.strip()
        or f"exit status {result.returncode}"
    )
