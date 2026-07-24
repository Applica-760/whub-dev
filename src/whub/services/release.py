"""Build and verify immutable operation releases."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
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


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
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


# build ----------------------------------------------------------------------


@dataclass(frozen=True)
class ReleaseBuild:
    """A wheel staged for a later verify operation."""

    release_id: str
    wheel_path: Path


def _source_release(source: Path) -> ReleaseInfo:
    pyproject_path = source / "pyproject.toml"
    app_path = source / "app"
    if not pyproject_path.is_file() or not app_path.is_dir():
        raise ReleaseBuildError(f"invalid whub development checkout: {source}")

    try:
        project = tomllib.loads(pyproject_path.read_text()).get("project", {})
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ReleaseBuildError(f"invalid pyproject.toml: {pyproject_path}") from error
    version = project.get("version") if isinstance(project, dict) else None
    if not isinstance(version, str) or not version:
        raise ReleaseBuildError(f"invalid project version: {pyproject_path}")

    status = _run(["git", "status", "--porcelain"], cwd=source)
    if status.stdout.strip():
        raise ReleaseBuildError("source worktree must be clean")
    commit = _run(["git", "rev-parse", "HEAD"], cwd=source).stdout.strip()
    if len(commit) != 40:
        raise ReleaseBuildError("source HEAD is invalid")
    return ReleaseInfo(version, commit)


def build_release(
    source: Path,
    *,
    context: WhubContext | None = None,
) -> ReleaseBuild:
    """Build a wheel in staging and stop the operation app during the build."""
    source = source.expanduser().resolve()
    context = context or current_context()
    release = _source_release(source)
    operation_whub = _operation_whub(context)
    staging = context.releases_dir / ".staging" / release.release_id
    artifact_dir = staging / "artifact"
    metadata_path = source / "src" / "whub" / "_build.json"
    app_stopped = False

    if (staging / "release.json").exists():
        raise ReleaseBuildError(f"release is already verified: {release.release_id}")

    try:
        _run([str(operation_whub), "app", "down"], cwd=source)
        app_stopped = True
        artifact_dir.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "package_version": release.package_version,
                    "source_commit": release.source_commit,
                }
            )
            + "\n"
        )
        _run(["npm", "run", "build"], cwd=source / "app")
        _run(
            ["uv", "build", "--wheel", "--out-dir", str(artifact_dir), "--clear"],
            cwd=source,
        )
        wheels = list(artifact_dir.glob("whub-*.whl"))
        if len(wheels) != 1:
            raise ReleaseBuildError(f"expected one wheel in {artifact_dir}")
        return ReleaseBuild(release.release_id, wheels[0])
    except ReleaseBuildError as error:
        if app_stopped:
            try:
                _restart_operation_app(operation_whub, cwd=source)
            except ReleaseBuildError as restart_error:
                raise ReleaseBuildError(f"{error}; failed to restart app: {restart_error}") from error
        raise
    finally:
        metadata_path.unlink(missing_ok=True)


# verify ---------------------------------------------------------------------


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
            if "whub = " not in entry_points or "wflow = " not in entry_points:
                raise ReleaseVerifyError("wheel does not contain whub and wflow entry points")
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


def _wheel_sha256(wheel_path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with wheel_path.open("rb") as wheel:
            for chunk in iter(lambda: wheel.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ReleaseVerifyError(f"cannot read wheel: {wheel_path}") from error
    return digest.hexdigest()


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

    operation_whub = _operation_whub(context)
    wheel_path = wheels[0]
    try:
        release = _verified_release_info(wheel_path, release_id)
        wheel_sha256 = _wheel_sha256(wheel_path)
        venv = staging / "venv"
        _run(["uv", "venv", "--clear", "--no-project", str(venv)], cwd=staging)
        python = venv / "bin" / "python"
        _run(["uv", "pip", "install", "--python", str(python), str(wheel_path)], cwd=staging)
        whub = venv / "bin" / "whub"
        version = _run([str(whub), "--version"], cwd=staging).stdout.strip()
        if version != f"whub, version {release.display}":
            raise ReleaseVerifyError("staging whub version does not match release")
        _run([str(venv / "bin" / "wflow"), "--help"], cwd=staging)
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
    except (OSError, ReleaseBuildError, ReleaseVerifyError) as caught:
        error = (
            caught
            if isinstance(caught, ReleaseVerifyError)
            else ReleaseVerifyError(str(caught))
        )
        try:
            _restart_operation_app(operation_whub, cwd=staging)
        except ReleaseBuildError as restart_error:
            raise ReleaseVerifyError(f"{error}; failed to restart app: {restart_error}") from error
        if error is caught:
            raise
        raise error from caught
