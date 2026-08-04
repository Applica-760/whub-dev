"""Shared helpers for operation releases."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

from whub.core.context import WhubContext
from whub.services.errors import ServiceError


# shared ---------------------------------------------------------------------


class ReleaseCommandError(ServiceError):
    """Raised when a shared operation release command fails."""


_INHERITED_INTERPRETER_VARS = ("PYTHONPATH", "VIRTUAL_ENV")


def _isolated_env() -> dict[str, str]:
    """Drop the caller's interpreter overrides so a venv resolves its own packages."""
    return {
        key: value
        for key, value in os.environ.items()
        if key not in _INHERITED_INTERPRETER_VARS
    }


def _run(
    command: list[str],
    *,
    cwd: Path,
    isolated: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=_isolated_env() if isolated else None,
        )
    except OSError as error:
        raise ReleaseCommandError(f"failed to run {' '.join(command)}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise ReleaseCommandError(f"{' '.join(command)}: {detail}")
    return result


def _operation_whub(context: WhubContext) -> Path:
    executable = context.releases_dir / "current" / "venv" / "bin" / "whub"
    if not executable.is_file():
        raise ReleaseCommandError(f"operation whub not found: {executable}")
    return executable


def _wheel_sha256(wheel_path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with wheel_path.open("rb") as wheel:
            for chunk in iter(lambda: wheel.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ReleaseCommandError(f"cannot read wheel: {wheel_path}") from error
    return digest.hexdigest()


def _restart_operation_app(executable: Path, *, cwd: Path) -> None:
    _run([str(executable), "app"], cwd=cwd)
