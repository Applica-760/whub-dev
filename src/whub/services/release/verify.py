"""Operation release verification service."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import zipfile

from whub.core.context import WhubContext, current_context
from whub.core.release import ReleaseInfo
from whub.services.errors import ServiceError
from whub.services.release.shared import ReleaseCommandError, _operation_whub, _restart_operation_app, _run, _wheel_sha256


class ReleaseVerifyError(ServiceError):
    """Raised when an operation release artifact cannot be verified."""


@dataclass(frozen=True)
class ReleaseVerification:
    """A verified operation release staged for later application."""

    release_id: str
    wheel_path: Path
    wheel_sha256: str


def _verified_release_info(wheel_path: Path, release_id: str) -> ReleaseInfo:
    try:
        with zipfile.ZipFile(wheel_path) as wheel:
            names = wheel.namelist()
            if "whub/webapp/dist/index.html" not in names:
                raise ReleaseVerifyError("wheel does not contain webapp index.html")
            if not any(name.startswith("whub/webapp/dist/assets/") for name in names):
                raise ReleaseVerifyError("wheel does not contain webapp assets")
            metadata_names = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
            if len(metadata_names) != 1:
                raise ReleaseVerifyError("wheel entry points are invalid")
            entry_points = wheel.read(metadata_names[0]).decode()
            if "whub = " not in entry_points:
                raise ReleaseVerifyError("wheel does not contain whub entry point")
            metadata = json.loads(wheel.read("whub/_build.json"))
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise ReleaseVerifyError(f"invalid wheel: {wheel_path}") from error

    if not isinstance(metadata, dict) or metadata.get("schema_version") != 1:
        raise ReleaseVerifyError("wheel build metadata is invalid")
    version = metadata.get("package_version")
    commit = metadata.get("source_commit")
    if (
        not isinstance(version, str)
        or not isinstance(commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit) is None
    ):
        raise ReleaseVerifyError("wheel build metadata is invalid")
    release = ReleaseInfo(version, commit)
    if release.release_id != release_id:
        raise ReleaseVerifyError(f"wheel release does not match: {release_id}")
    return release


def verify_release(
    release_id: str,
    *,
    context: WhubContext | None = None,
) -> ReleaseVerification:
    """Verify a staged wheel and create its immutable release record."""
    context = context or current_context()
    staging = context.releases_dir / ".staging" / release_id
    artifact_dir = staging / "artifact"
    wheels = list(artifact_dir.glob("whub-*.whl"))
    if len(wheels) != 1:
        raise ReleaseVerifyError(f"expected one wheel in {artifact_dir}")
    release_json = staging / "release.json"
    if release_json.exists():
        raise ReleaseVerifyError(f"release is already verified: {release_id}")

    try:
        operation_whub = _operation_whub(context)
    except ReleaseCommandError as error:
        raise ReleaseVerifyError(str(error)) from error
    wheel_path = wheels[0]
    try:
        release = _verified_release_info(wheel_path, release_id)
        wheel_sha256 = _wheel_sha256(wheel_path)
        venv = staging / "venv"
        # 検証はwheel由来の実装だけを見る。呼び出し側のPYTHONPATH/VIRTUAL_ENVは遮断する
        _run(
            ["uv", "venv", "--clear", "--no-project", str(venv)],
            cwd=staging,
            isolated=True,
        )
        python = venv / "bin" / "python"
        _run(
            ["uv", "pip", "install", "--python", str(python), str(wheel_path)],
            cwd=staging,
            isolated=True,
        )
        whub = venv / "bin" / "whub"
        version = _run(
            [str(whub), "--version"], cwd=staging, isolated=True
        ).stdout.strip()
        if version != f"whub, version {release.display}":
            raise ReleaseVerifyError("staging whub version does not match release")
        release_json.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "release_id": release.release_id,
                    "wheel_sha256": wheel_sha256,
                    "verified": True,
                }
            )
            + "\n"
        )
        return ReleaseVerification(release.release_id, wheel_path, wheel_sha256)
    except (OSError, ReleaseCommandError, ReleaseVerifyError) as caught:
        error = (
            caught
            if isinstance(caught, ReleaseVerifyError)
            else ReleaseVerifyError(str(caught))
        )
        try:
            _restart_operation_app(operation_whub, cwd=staging)
        except ReleaseCommandError as restart_error:
            raise ReleaseVerifyError(f"{error}; failed to restart app: {restart_error}") from error
        if error is caught:
            raise
        raise error from caught
