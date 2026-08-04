"""Operation release application service."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

from whub.core.context import WhubContext, current_context
from whub.services.errors import ServiceError
from whub.services.release.shared import ReleaseCommandError, _operation_whub, _restart_operation_app, _run, _wheel_sha256


class ReleaseApplyError(ServiceError):
    """Raised when a verified operation release cannot be applied."""


@dataclass(frozen=True)
class ReleaseApplication:
    """An operation release made current."""

    release_id: str
    release_path: Path


def _staging_release(context: WhubContext, release_id: str) -> Path:
    if not release_id or Path(release_id).name != release_id:
        raise ReleaseApplyError(f"invalid release id: {release_id}")
    return context.releases_dir / ".staging" / release_id


def _apply_ready_release(staging: Path, release_id: str) -> None:
    release_json = staging / "release.json"
    try:
        record = json.loads(release_json.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseApplyError(f"invalid verified release: {release_id}") from error
    if (
        not isinstance(record, dict)
        or record.get("schema_version") != 1
        or record.get("release_id") != release_id
        or record.get("verified") is not True
        or not isinstance(record.get("wheel_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", record["wheel_sha256"]) is None
    ):
        raise ReleaseApplyError(f"invalid verified release: {release_id}")

    wheels = list((staging / "artifact").glob("whub-*.whl"))
    if len(wheels) != 1 or _wheel_sha256(wheels[0]) != record["wheel_sha256"]:
        raise ReleaseApplyError(f"verified wheel does not match: {release_id}")
    executable = staging / "venv" / "bin" / "whub"
    if not executable.is_file():
        raise ReleaseApplyError(f"verified venv is missing: {release_id}")


def _current_release(context: WhubContext) -> Path:
    current = context.releases_dir / "current"
    try:
        target = current.resolve(strict=True)
    except OSError as error:
        raise ReleaseApplyError(f"current release is invalid: {current}") from error
    if target.parent != context.releases_dir:
        raise ReleaseApplyError(f"current release is invalid: {current}")
    return target


def _replace_current(context: WhubContext, target: Path) -> None:
    current = context.releases_dir / "current"
    temporary = context.releases_dir / "current.tmp"
    if temporary.exists() or temporary.is_symlink():
        raise ReleaseApplyError(f"temporary current link exists: {temporary}")
    try:
        os.symlink(target, temporary)
        os.replace(temporary, current)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise ReleaseApplyError(f"failed to switch current release: {error}") from error


def _install_release_venv(release_path: Path) -> None:
    wheels = list((release_path / "artifact").glob("whub-*.whl"))
    if len(wheels) != 1:
        raise ReleaseApplyError(f"expected one wheel in {release_path / 'artifact'}")
    venv = release_path / "venv"
    # 配置後のvenvもwheel由来の実装だけで成立させる
    _run(
        ["uv", "venv", "--clear", "--no-project", str(venv)],
        cwd=release_path,
        isolated=True,
    )
    _run(
        ["uv", "pip", "install", "--python", str(venv / "bin" / "python"), str(wheels[0])],
        cwd=release_path,
        isolated=True,
    )
    _run([str(venv / "bin" / "whub"), "--version"], cwd=release_path, isolated=True)


def apply_release(
    release_id: str,
    *,
    context: WhubContext | None = None,
) -> ReleaseApplication:
    """Make a verified staging release current and start its app."""
    context = context or current_context()
    staging = _staging_release(context, release_id)
    target = context.releases_dir / release_id
    if target.exists() or target.is_symlink():
        raise ReleaseApplyError(f"release already exists: {release_id}")
    _apply_ready_release(staging, release_id)
    old_release = _current_release(context)
    try:
        old_whub = _operation_whub(context)
    except ReleaseCommandError as error:
        raise ReleaseApplyError(str(error)) from error
    moved = False
    switched = False

    try:
        os.replace(staging, target)
        moved = True
        _install_release_venv(target)
        _replace_current(context, target)
        switched = True
        _run([str(target / "venv" / "bin" / "whub"), "app"], cwd=target)
        return ReleaseApplication(release_id, target)
    except (OSError, ReleaseApplyError, ReleaseCommandError) as caught:
        error = (
            caught
            if isinstance(caught, ReleaseApplyError)
            else ReleaseApplyError(str(caught))
        )
        try:
            if switched:
                _replace_current(context, old_release)
            if moved:
                os.replace(target, staging)
                _install_release_venv(staging)
            _restart_operation_app(old_whub, cwd=old_release)
        except (OSError, ReleaseApplyError, ReleaseCommandError) as rollback_error:
            raise ReleaseApplyError(f"{error}; failed to restore old release: {rollback_error}") from error
        if error is caught:
            raise
        raise error from caught
