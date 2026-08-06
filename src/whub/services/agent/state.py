"""Persistence and cleanup for Agent-generated files."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

import yaml

from whub.services.errors import ServiceError
from whub.services.agent.context import CONTEXT_MARKERS, AgentContext
from whub.utils.managed_block import managed_range


@dataclass(frozen=True)
class _AgentState:
    project: str
    task_id: str
    worktree: Path
    files: Mapping[PurePosixPath, str]
    blocks: Mapping[PurePosixPath, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Materialization:
    files: Mapping[PurePosixPath, str] = field(default_factory=dict)
    blocks: Mapping[PurePosixPath, str] = field(default_factory=dict)


# --- Agent configuration lifecycle ------------------------------------------


def prepare(
    workspace_root: Path,
    project: str,
    task_id: str,
    worktree: Path,
    auth_files: Mapping[PurePosixPath, str],
    agent_context: AgentContext = AgentContext({}, {}),
) -> None:
    """Materialize auth settings, then context, and persist their ownership."""
    path = _state_path(workspace_root, project, task_id)
    previous = _load(path)
    if previous is not None:
        _validate(previous, project, task_id, worktree)
    auth = _materialize_auth(worktree, auth_files)
    context = _materialize_context(
        worktree, agent_context, {} if previous is None else previous.blocks
    )
    files = dict({} if previous is None else previous.files)
    blocks = dict({} if previous is None else previous.blocks)
    files.update(auth.files)
    files.update(context.files)
    blocks.update(auth.blocks)
    blocks.update(context.blocks)
    state = _AgentState(
        project,
        task_id,
        worktree,
        files,
        blocks,
    )
    if state.files or state.blocks:
        _save(path, state)


def cleanup(workspace_root: Path, project: str, task_id: str, worktree: Path) -> None:
    """Remove unchanged files owned by this Agent, then its state record."""
    path = _state_path(workspace_root, project, task_id)
    state = _load(path)
    if state is None:
        return
    _validate(state, project, task_id, worktree)
    files: list[Path] = []
    for relative, expected_hash in state.files.items():
        target = _safe_path(worktree, relative)
        if not target.exists():
            continue
        if not target.is_file():
            raise ServiceError(
                f"generated config is no longer a regular file: {relative}"
            )
        if _digest(target.read_bytes()) != expected_hash:
            raise ServiceError(
                f"generated config was modified and was not removed: {relative}"
            )
        files.append(target)

    blocks: list[tuple[Path, int, int]] = []
    for relative, expected_hash in state.blocks.items():
        target = _safe_path(worktree, relative)
        if not target.exists() or not target.is_file():
            raise ServiceError(f"managed context is missing: {relative}")
        content = target.read_text()
        start, end = _block_range(content, relative)
        block = content[start:end]
        if _digest(block.encode()) != expected_hash:
            raise ServiceError(
                f"managed context was modified and was not removed: {relative}"
            )
        blocks.append((target, start, end))

    for target, start, end in blocks:
        content = target.read_text()
        before = content[:start]
        if before.endswith("\n\n"):
            before = before[:-1]
        remaining = before + content[end:]
        if remaining.strip():
            target.write_text(remaining, encoding="utf-8", newline="\n")
        else:
            target.unlink()
    for target in files:
        target.unlink()
    _remove_empty_parents(worktree, (*state.files, *state.blocks))
    path.unlink()


def owned_paths(
    workspace_root: Path, project: str, task_id: str, worktree: Path
) -> set[PurePosixPath]:
    """Return paths owned wholly or partly by the local Agent lifecycle."""
    state = _load(_state_path(workspace_root, project, task_id))
    if state is None:
        return set()
    _validate(state, project, task_id, worktree)
    return set(state.files) | set(state.blocks)


def _state_path(workspace_root: Path, project: str, task_id: str) -> Path:
    number = task_id.removeprefix("TASK-")
    return (
        workspace_root
        / "projects"
        / "worktrees"
        / "agents"
        / f"{project}-{number}.yaml"
    )


# --- Generated file materialization -----------------------------------------


def _materialize_auth(
    worktree: Path,
    files: Mapping[PurePosixPath, str],
) -> _Materialization:
    return _Materialization(files=_materialize_files(worktree, files))


def _materialize_files(
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
        created[relative] = _digest(target.read_bytes())
    return created


def _materialize_context(
    worktree: Path,
    context: AgentContext,
    owned_blocks: Mapping[PurePosixPath, str],
) -> _Materialization:
    return _Materialization(
        files=_materialize_files(worktree, context.files),
        blocks=_apply_context_blocks(worktree, context.blocks, owned_blocks),
    )


# --- Managed context blocks --------------------------------------------------


def _apply_context_blocks(
    worktree: Path,
    patches: Mapping[PurePosixPath, str],
    owned: Mapping[PurePosixPath, str],
) -> dict[PurePosixPath, str]:
    created: dict[PurePosixPath, str] = {}
    for relative, block in patches.items():
        _block_range(block, relative)
        target = _safe_path(worktree, relative)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(block, encoding="utf-8", newline="\n")
            created[relative] = _digest(block.encode())
            continue
        if not target.is_file():
            raise ServiceError(f"managed context is not a regular file: {relative}")
        content = target.read_text()
        try:
            start, end = _block_range(content, relative)
        except ServiceError:
            if relative in owned:
                raise ServiceError(f"managed context is missing: {relative}") from None
            separator = "" if not content or content.endswith("\n\n") else "\n"
            target.write_text(
                content + separator + block, encoding="utf-8", newline="\n"
            )
            created[relative] = _digest(block.encode())
            continue
        if relative not in owned:
            raise ServiceError(f"managed context already exists: {relative}")
        if _digest(content[start:end].encode()) != owned[relative]:
            raise ServiceError(f"managed context was modified: {relative}")
    return created


# --- File safety and content checks -----------------------------------------


def _remove_empty_parents(worktree: Path, files: tuple[PurePosixPath, ...]) -> None:
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


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _block_range(content: str, relative: PurePosixPath) -> tuple[int, int]:
    try:
        bounds = managed_range(content, CONTEXT_MARKERS)
    except ValueError as error:
        raise ServiceError(f"invalid managed context: {relative}") from error
    if bounds is None:
        raise ServiceError(f"managed context is missing: {relative}")
    return bounds


# --- State persistence -------------------------------------------------------


def _load(path: Path) -> _AgentState | None:
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text())
        files = data["files"]
        if data.get("schema_version") != 3 or not isinstance(files, dict):
            raise ValueError("invalid schema")
        parsed = {PurePosixPath(name): digest for name, digest in files.items()}
        blocks = data.get("blocks")
        if not isinstance(blocks, dict):
            raise ValueError("invalid blocks")
        parsed_blocks = {PurePosixPath(name): digest for name, digest in blocks.items()}
        if any(
            path.is_absolute() or ".." in path.parts
            for path in (*parsed, *parsed_blocks)
        ):
            raise ValueError("files must be relative")
        return _AgentState(
            data["project"],
            data["task_id"],
            Path(data["worktree"]),
            parsed,
            parsed_blocks,
        )
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        raise ServiceError(f"invalid Agent state: {path}: {error}") from error


def _save(path: Path, state: _AgentState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 3,
        "project": state.project,
        "task_id": state.task_id,
        "worktree": str(state.worktree),
        "files": {str(name): digest for name, digest in state.files.items()},
        "blocks": {str(name): digest for name, digest in state.blocks.items()},
    }
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        yaml.safe_dump(data, temporary, sort_keys=False)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _validate(state: _AgentState, project: str, task_id: str, worktree: Path) -> None:
    if (state.project, state.task_id, state.worktree) != (project, task_id, worktree):
        raise ServiceError("Agent state does not match the registered worktree")
