"""Persistence for workspace-owned worktree definitions."""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
import tempfile

import yaml
from pydantic import ValidationError

from whub.models import WorktreeDefinition, WorktreeDefinitionRecord
from whub.services.errors import ServiceError


def worktree_definitions_dir(workspace_root: Path) -> Path:
    """Return the workspace-owned directory holding worktree definitions."""
    return workspace_root / "projects" / "worktrees"


def worktree_definition_path(
    workspace_root: Path, definition: WorktreeDefinition
) -> Path:
    """Return the canonical YAML path for DEFINITION."""
    number = definition.task_id.removeprefix("TASK-")
    return (
        worktree_definitions_dir(workspace_root)
        / f"{definition.parent_project}-{number}.yaml"
    )


def save_worktree_definition(
    workspace_root: Path, definition: WorktreeDefinition
) -> Path:
    """Atomically create a unique worktree definition beneath WORKSPACE_ROOT."""
    directory = worktree_definitions_dir(workspace_root)
    directory.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(
        directory / ".worktree-definitions.lock", os.O_CREAT | os.O_RDWR, 0o600
    )
    with os.fdopen(lock_fd, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _reject_duplicate_definition(workspace_root, definition)
        destination = worktree_definition_path(workspace_root, definition)
        _create_definition_file(destination, definition)
    return destination


def list_worktree_definitions(workspace_root: Path) -> list[WorktreeDefinitionRecord]:
    """Discover definition YAMLs and report recoverable inconsistencies."""
    directory = worktree_definitions_dir(workspace_root)
    if not directory.is_dir():
        return []
    return [
        _definition_record(workspace_root, path)
        for path in sorted(directory.glob("*.yaml"))
    ]


def _reject_duplicate_definition(
    workspace_root: Path, candidate: WorktreeDefinition
) -> None:
    for record in list_worktree_definitions(workspace_root):
        definition = record.definition
        if definition is not None and (
            definition.parent_project,
            definition.task_id,
        ) == (
            candidate.parent_project,
            candidate.task_id,
        ):
            raise ServiceError(
                f"duplicate worktree task: {candidate.parent_project}/{candidate.task_id}"
            )


def _create_definition_file(path: Path, definition: WorktreeDefinition) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            yaml.safe_dump(
                definition.model_dump(mode="json"),
                temporary,
                allow_unicode=True,
                sort_keys=False,
            )
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.link(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError as error:
        raise ServiceError(
            f"worktree definition already exists: {path.name}"
        ) from error
    except OSError as error:
        raise ServiceError(
            f"failed to save worktree definition: {path}: {error}"
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _definition_record(workspace_root: Path, path: Path) -> WorktreeDefinitionRecord:
    try:
        definition = WorktreeDefinition.model_validate(yaml.safe_load(path.read_text()))
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as error:
        return WorktreeDefinitionRecord(
            path, None, (f"invalid worktree definition YAML: {path.name}: {error}",)
        )

    number = definition.task_id.removeprefix("TASK-")
    diagnostics: list[str] = []
    if path.name != f"{definition.parent_project}-{number}.yaml":
        diagnostics.append(
            f"worktree definition name does not match identity: {path.name}"
        )
    if not (workspace_root / definition.workspace_path).is_dir():
        diagnostics.append(
            f"worktree directory is missing: {definition.workspace_path}"
        )
    return WorktreeDefinitionRecord(path, definition, tuple(diagnostics))
