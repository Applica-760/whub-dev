"""Persistence and cleanup for Agent-harness generated files."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

import yaml

from whub.services.errors import ServiceError


@dataclass(frozen=True)
class HarnessState:
    project: str
    task_id: str
    worktree: Path
    files: Mapping[PurePosixPath, str]


def prepare(
    workspace_root: Path,
    project: str,
    task_id: str,
    worktree: Path,
    files: Mapping[PurePosixPath, str],
) -> None:
    """Materialize files and persist ownership of only newly created files."""
    path = state_path(workspace_root, project, task_id)
    state = load(path)
    if state is not None:
        _validate(state, project, task_id, worktree)
    created = _materialize(worktree, files)
    owned = {} if state is None else dict(state.files)
    owned.update(created)
    if owned:
        save(path, HarnessState(project, task_id, worktree, owned))


def cleanup(workspace_root: Path, project: str, task_id: str, worktree: Path) -> None:
    """Remove unchanged files owned by this harness, then its state record."""
    path = state_path(workspace_root, project, task_id)
    state = load(path)
    if state is None:
        return
    _validate(state, project, task_id, worktree)
    for relative, expected_hash in state.files.items():
        target = _safe_path(worktree, relative)
        if not target.exists():
            continue
        if not target.is_file():
            raise ServiceError(
                f"generated config is no longer a regular file: {relative}"
            )
        if _hash(target) != expected_hash:
            raise ServiceError(
                f"generated config was modified and was not removed: {relative}"
            )
        target.unlink()
    _remove_empty_parents(worktree, state.files)
    path.unlink()


def state_path(workspace_root: Path, project: str, task_id: str) -> Path:
    number = task_id.removeprefix("TASK-")
    return (
        workspace_root
        / "projects"
        / "worktrees"
        / "agents"
        / f"{project}-{number}.yaml"
    )


def _materialize(
    worktree: Path, files: Mapping[PurePosixPath, str]
) -> dict[PurePosixPath, str]:
    created: dict[PurePosixPath, str] = {}
    for relative, content in files.items():
        target = _safe_path(worktree, relative)
        if target.exists():
            if not target.is_file() or not _matches_content(target, content):
                raise ServiceError(f"generated config already exists: {relative}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        created[relative] = _hash(target)
    return created


def _remove_empty_parents(worktree: Path, files: Mapping[PurePosixPath, str]) -> None:
    parents = {
        parent
        for relative in files
        for parent in relative.parents
        if parent != PurePosixPath(".")
    }
    for relative in sorted(parents, key=lambda path: len(path.parts), reverse=True):
        try:
            _safe_path(worktree, relative).rmdir()
        except OSError:
            continue


def _safe_path(worktree: Path, relative: PurePosixPath) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ServiceError(f"invalid generated config path: {relative}")
    target = worktree
    for part in relative.parts:
        target /= part
        if target.is_symlink():
            raise ServiceError(f"generated config path is a symlink: {relative}")
    return target


def _matches_content(path: Path, expected: str) -> bool:
    actual = path.read_text()
    if actual == expected:
        return True
    if path.suffix != ".json":
        return False
    try:
        return json.loads(actual) == json.loads(expected)
    except json.JSONDecodeError:
        return False


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> HarnessState | None:
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text())
        files = data["files"]
        if data.get("schema_version") != 1 or not isinstance(files, dict):
            raise ValueError("invalid schema")
        parsed = {PurePosixPath(name): digest for name, digest in files.items()}
        if any(path.is_absolute() or ".." in path.parts for path in parsed):
            raise ValueError("files must be relative")
        return HarnessState(
            data["project"], data["task_id"], Path(data["worktree"]), parsed
        )
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        raise ServiceError(f"invalid Agent harness state: {path}: {error}") from error


def save(path: Path, state: HarnessState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "project": state.project,
        "task_id": state.task_id,
        "worktree": str(state.worktree),
        "files": {str(name): digest for name, digest in state.files.items()},
    }
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        yaml.safe_dump(data, temporary, sort_keys=False)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _validate(state: HarnessState, project: str, task_id: str, worktree: Path) -> None:
    if (state.project, state.task_id, state.worktree) != (project, task_id, worktree):
        raise ServiceError("Agent harness state does not match the registered worktree")
