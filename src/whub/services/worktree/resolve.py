"""Resolve resource-specific worktree locations and lifecycle inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from whub.models import Host, Manifest, RemoteResource, SymlinkResource, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.task import load_project_task


LOCAL_WORKTREE_ROOT = Path("projects/worktrees")


@dataclass(frozen=True)
class ResolvedProjectWorktree:
    """One registered worktree and the resource that owns its Git operations."""

    definition: WorktreeDefinition
    parent: Path | str
    destination: Path | str
    base_branch: str
    host: Host | None = None

    @property
    def workspace_path(self) -> str:
        return str(self.destination)

    @property
    def is_remote(self) -> bool:
        return self.host is not None


def _resolve_worktree_resource(
    manifest: Manifest, project: str
) -> SymlinkResource | RemoteResource:
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    resource = resolved_project.resource
    if resource is None:
        raise ServiceError(f"project has no resource: {project}")
    return resource


def _require_worktree_resource(
    manifest: Manifest, project: str
) -> SymlinkResource | RemoteResource:
    resource = _resolve_worktree_resource(manifest, project)
    if resource.git is None:
        raise ServiceError(f"worktree parent has no git declaration: {project}")
    return resource


def _worktree_name(definition: WorktreeDefinition) -> str:
    return f"{definition.parent_project}-{definition.task_id.removeprefix('TASK-')}"


def _resolve_location(
    manifest: Manifest, workspace_root: Path, definition: WorktreeDefinition
) -> tuple[Path | str, Path | str, Host | None]:
    resource = _resolve_worktree_resource(manifest, definition.parent_project)

    if isinstance(resource, SymlinkResource):
        return (
            Path(resource.source),
            workspace_root / LOCAL_WORKTREE_ROOT / _worktree_name(definition),
            None,
        )
    if isinstance(resource, RemoteResource):
        host = manifest.hosts[resource.host]
        parent = str(PurePosixPath(host.mount_root) / resource.path)
        destination = str(
            PurePosixPath(host.mount_root) / host.worktree_root / _worktree_name(definition)
        )
        return parent, destination, host
    raise AssertionError(f"unsupported resource: {resource!r}")


def resolve_worktree_parent(manifest: Manifest, definition: WorktreeDefinition) -> Path:
    """Resolve a local worktree parent for APIs that are intentionally local-only."""
    resource = _require_worktree_resource(manifest, definition.parent_project)
    if not isinstance(resource, SymlinkResource):
        raise ServiceError(f"not a local resource: {definition.parent_project}")
    return Path(resource.source)


def resolve_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> ResolvedProjectWorktree:
    """Resolve one cleanly registered worktree and its PR lifecycle inputs."""
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
    resource = _require_worktree_resource(manifest, project)
    assert resource.git is not None
    if resource.git.branch is None:
        raise ServiceError(f"worktree parent has no git branch declaration: {project}")
    load_project_task(manifest, project, definition.task_id)
    parent, destination, host = _resolve_location(manifest, workspace_root, definition)
    return ResolvedProjectWorktree(
        definition=definition,
        parent=parent,
        destination=destination,
        base_branch=resource.git.branch,
        host=host,
    )
