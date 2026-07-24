"""Build operation release artifacts from an explicit development checkout."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import tomllib

from whub.core.context import WhubContext, current_context
from whub.core.release import ReleaseInfo
from whub.services.errors import ServiceError


class ReleaseBuildError(ServiceError):
    """Raised when an operation release artifact cannot be built."""


@dataclass(frozen=True)
class ReleaseBuild:
    """A wheel staged for a later verify operation."""

    release_id: str
    wheel_path: Path


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    except OSError as error:
        raise ReleaseBuildError(f"failed to run {' '.join(command)}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise ReleaseBuildError(f"{' '.join(command)}: {detail}")
    return result


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


def _operation_whub(context: WhubContext) -> Path:
    executable = context.releases_dir / "current" / "venv" / "bin" / "whub"
    if not executable.is_file():
        raise ReleaseBuildError(f"operation whub not found: {executable}")
    return executable


def _restart_operation_app(executable: Path, *, cwd: Path) -> None:
    _run([str(executable), "app"], cwd=cwd)


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
        _run(
            ["npm", "run", "build"],
            cwd=source / "app",
        )
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
