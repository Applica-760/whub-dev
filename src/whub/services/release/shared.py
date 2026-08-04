"""Shared helpers for operation releases."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import zipfile

from whub.core.context import WhubContext, current_context
from whub.core.release import ReleaseInfo
from whub.services.errors import ServiceError


# shared ---------------------------------------------------------------------


class ReleaseBuildError(ServiceError):
    """Raised when an operation release artifact cannot be built."""


class ReleaseVerifyError(ServiceError):
    """Raised when an operation release artifact cannot be verified."""


class ReleaseApplyError(ServiceError):
    """Raised when a verified operation release cannot be applied."""


_ROLLUP_NATIVE_DEPENDENCY = re.compile(r"@rollup/rollup-[a-z0-9-]+")


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
        raise ReleaseBuildError(f"failed to run {' '.join(command)}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise ReleaseBuildError(f"{' '.join(command)}: {detail}")
    return result


def _operation_whub(context: WhubContext) -> Path:
    executable = context.releases_dir / "current" / "venv" / "bin" / "whub"
    if not executable.is_file():
        raise ReleaseBuildError(f"operation whub not found: {executable}")
    return executable


def _restart_operation_app(executable: Path, *, cwd: Path) -> None:
    _run([str(executable), "app"], cwd=cwd)


def _stop_operation_app(*, cwd: Path) -> None:
    _run([sys.executable, "-m", "whub", "app", "down"], cwd=cwd)


