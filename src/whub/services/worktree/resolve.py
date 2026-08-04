"""Resolve registered worktrees and their GitHub PR inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whub.models import Manifest, RemoteResource, SymlinkResource, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.task import load_project_task


@dataclass(frozen=True)
class ResolvedProjectWorktree:
    """One consistent registered worktree and its PR lifecycle inputs."""

    definition: WorktreeDefinition
    parent: Path
    destination: Path
    base_branch: str


def _require_worktree_parent(manifest: Manifest, project: str) -> SymlinkResource:
    """Resolve a Project eligible to own a local Git worktree."""
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    resource = resolved_project.resource
    if resource is None:
        raise ServiceError(f"project has no resource: {project}")
    if isinstance(resource, RemoteResource):
        raise ServiceError(
            f"worktree for remote resource is not implemented: {project}"
        )
    if not isinstance(resource, SymlinkResource):
        raise ServiceError(f"not a local resource: {project}")
    if resource.git is None:
        raise ServiceError(f"worktree parent has no git declaration: {project}")
    return resource


def resolve_worktree_parent(manifest: Manifest, definition: WorktreeDefinition) -> Path:
    """Resolve DEFINITION's current local parent repository path."""
    return Path(_require_worktree_parent(manifest, definition.parent_project).source)


def resolve_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> ResolvedProjectWorktree:
    """Resolve one cleanly registered worktree and its GitHub PR inputs."""
    from whub.services.worktree.check import inspect_worktrees

    inspection = next(
        (
            item
            for item in inspect_worktrees(manifest, workspace_root)
            if item.definition is not None
            and item.definition.parent_project == project
            and item.definition.task_id == task_id
        ),
        None,
    )
    if inspection is None:
        raise ServiceError(f"worktree definition not found: {project}/{task_id}")
    if inspection.diagnostics:
        raise ServiceError(
            "cannot use inconsistent worktree: " + "; ".join(inspection.diagnostics)
        )
    definition = inspection.definition
    assert definition is not None
    resource = _require_worktree_parent(manifest, project)
    assert resource.git is not None
    if resource.git.branch is None:
        raise ServiceError(f"worktree parent has no git branch declaration: {project}")
    load_project_task(manifest, project, definition.task_id)
    return ResolvedProjectWorktree(
        definition=definition,
        parent=Path(resource.source),
        destination=workspace_root / definition.workspace_path,
        base_branch=resource.git.branch,
    )
