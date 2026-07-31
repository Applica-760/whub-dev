"""Persistence and cleanup for Agent-harness generated files."""

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


@dataclass(frozen=True)
class HarnessState:
    project: str
    task_id: str
    worktree: Path
    files: Mapping[PurePosixPath, str]
    patches: Mapping[PurePosixPath, str] = field(default_factory=dict)


_CONTEXT_START = "<!-- whub:harness:context:start -->"
_CONTEXT_END = "<!-- whub:harness:context:end -->"


def prepare(
    workspace_root: Path,
    project: str,
    task_id: str,
    worktree: Path,
    files: Mapping[PurePosixPath, str],
    patches: Mapping[PurePosixPath, str] | None = None,
) -> None:
    """Materialize Agent settings and Hub context, then persist their ownership."""
    path = state_path(workspace_root, project, task_id)
    state = load(path)
    if state is not None:
        _validate(state, project, task_id, worktree)
    hub_files, hub_patches = _hub_context(workspace_root)
    materialized = dict(hub_files)
    materialized.update(files)
    managed = dict(hub_patches)
    managed.update(patches or {})
    created = _materialize(worktree, materialized)
    owned = {} if state is None else dict(state.files)
    owned.update(created)
    owned_patches = {} if state is None else dict(state.patches)
    owned_patches.update(_apply_patches(worktree, managed, owned_patches))
    if owned or owned_patches:
        save(path, HarnessState(project, task_id, worktree, owned, owned_patches))


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
    for relative, expected_hash in state.patches.items():
        target = _safe_path(worktree, relative)
        if not target.exists() or not target.is_file():
            raise ServiceError(f"managed context is missing: {relative}")
        content = target.read_text()
        start, end = _context_bounds(content, relative)
        block = content[start:end]
        if _hash_content(block) != expected_hash:
            raise ServiceError(f"managed context was modified and was not removed: {relative}")
        before = content[:start]
        if before.endswith("\n\n"):
            before = before[:-1]
        remaining = before + content[end:]
        if remaining.strip():
            target.write_text(remaining, encoding="utf-8", newline="\n")
        else:
            target.unlink()
    _remove_empty_parents(worktree, (*state.files, *state.patches))
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


def _hub_context(
    workspace_root: Path,
) -> tuple[dict[PurePosixPath, str], dict[PurePosixPath, str]]:
    rules = workspace_root / "AGENTS.md"
    if not rules.is_file():
        return {}, {}
    skills = workspace_root / ".agents/skills"
    files: dict[PurePosixPath, str] = {}
    if skills.exists():
        if not skills.is_dir() or skills.is_symlink():
            raise ServiceError(f"Hub Skills directory is invalid: {skills}")
        for source in sorted(skills.rglob("*")):
            if source.is_dir():
                continue
            if source.is_symlink() or not source.is_file():
                raise ServiceError(f"Hub Skill is not a regular file: {source}")
            files[PurePosixPath(".agents/skills") / source.relative_to(skills)] = (
                source.read_text()
            )
    return files, {
        PurePosixPath("AGENTS.md"): _context_block(
            "# Hub common rules\n"
            f"Relative paths in this block are relative to Hub root: {workspace_root}\n\n"
            f"{rules.read_text().rstrip()}\n"
        ),
        PurePosixPath(".claude/CLAUDE.md"): _context_block("@../AGENTS.md\n"),
    }


def _context_block(content: str) -> str:
    return f"{_CONTEXT_START}\n{content}{_CONTEXT_END}\n"


def _apply_patches(
    worktree: Path,
    patches: Mapping[PurePosixPath, str],
    owned: Mapping[PurePosixPath, str],
) -> dict[PurePosixPath, str]:
    created: dict[PurePosixPath, str] = {}
    for relative, block in patches.items():
        _context_bounds(block, relative)
        target = _safe_path(worktree, relative)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(block, encoding="utf-8", newline="\n")
            created[relative] = _hash_content(block)
            continue
        if not target.is_file():
            raise ServiceError(f"managed context is not a regular file: {relative}")
        content = target.read_text()
        try:
            start, end = _context_bounds(content, relative)
        except ServiceError:
            if relative in owned:
                raise ServiceError(f"managed context is missing: {relative}") from None
            separator = "" if not content or content.endswith("\n\n") else "\n"
            target.write_text(content + separator + block, encoding="utf-8", newline="\n")
            created[relative] = _hash_content(block)
            continue
        if relative not in owned:
            raise ServiceError(f"managed context already exists: {relative}")
        if _hash_content(content[start:end]) != owned[relative]:
            raise ServiceError(f"managed context was modified: {relative}")
    return created


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


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _context_bounds(content: str, relative: PurePosixPath) -> tuple[int, int]:
    start = content.find(_CONTEXT_START)
    if start < 0:
        raise ServiceError(f"managed context is missing: {relative}")
    end = content.find(_CONTEXT_END, start)
    if end < 0 or content.find(_CONTEXT_START, start + len(_CONTEXT_START)) >= 0:
        raise ServiceError(f"invalid managed context: {relative}")
    end += len(_CONTEXT_END)
    if end < len(content) and content[end] == "\n":
        end += 1
    return start, end


def load(path: Path) -> HarnessState | None:
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text())
        files = data["files"]
        if data.get("schema_version") not in {1, 2} or not isinstance(files, dict):
            raise ValueError("invalid schema")
        parsed = {PurePosixPath(name): digest for name, digest in files.items()}
        patches = data.get("patches", {})
        if not isinstance(patches, dict):
            raise ValueError("invalid patches")
        parsed_patches = {
            PurePosixPath(name): digest for name, digest in patches.items()
        }
        if any(
            path.is_absolute() or ".." in path.parts
            for path in (*parsed, *parsed_patches)
        ):
            raise ValueError("files must be relative")
        return HarnessState(
            data["project"],
            data["task_id"],
            Path(data["worktree"]),
            parsed,
            parsed_patches,
        )
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        raise ServiceError(f"invalid Agent harness state: {path}: {error}") from error


def save(path: Path, state: HarnessState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 2,
        "project": state.project,
        "task_id": state.task_id,
        "worktree": str(state.worktree),
        "files": {str(name): digest for name, digest in state.files.items()},
        "patches": {str(name): digest for name, digest in state.patches.items()},
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
