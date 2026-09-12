"""GitHub CLI execution and repository URL normalization."""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
from urllib.parse import urlparse

from whub.core.remote import run_ssh_command
from whub.models import Host


def run_gh(
    host: Host | None, directory: Path | str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run GitHub CLI in one local or remote repository directory."""
    if host is None:
        assert isinstance(directory, Path)
        return subprocess.run(
            ["gh", *arguments], cwd=directory, capture_output=True, text=True
        )
    assert isinstance(directory, str)
    return run_ssh_command(
        host,
        f"cd {shlex.quote(directory)} && gh {shlex.join(arguments)}",
    )


def github_repository(url: str) -> str:
    """Return GitHub OWNER/REPOSITORY from a supported Git remote URL."""
    value = url.removesuffix("/").removesuffix(".git")
    if value.startswith("git@github.com:"):
        path = value.removeprefix("git@github.com:")
    else:
        parsed = urlparse(value)
        if parsed.hostname != "github.com":
            raise ValueError(f"git.url is not a GitHub repository: {url}")
        path = parsed.path.removeprefix("/")
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"git.url is not a GitHub repository: {url}")
    return "/".join(parts)
