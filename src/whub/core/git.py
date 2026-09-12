"""Git command execution for local and remote repositories."""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from whub.core.remote import run_ssh_command
from whub.models import Host


def run_git(directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run Git in one local repository directory."""
    return subprocess.run(
        ["git", "-C", str(directory), *arguments], capture_output=True, text=True
    )


def run_remote_git(
    host: Host, directory: str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run Git in one remote repository directory."""
    command = f"git -C {shlex.quote(directory)} {shlex.join(arguments)}"
    return run_ssh_command(host, command)


def run_git_at(
    host: Host | None, directory: Path | str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run Git in one local or remote repository directory."""
    if host is None:
        assert isinstance(directory, Path)
        return run_git(directory, *arguments)
    assert isinstance(directory, str)
    return run_remote_git(host, directory, *arguments)
