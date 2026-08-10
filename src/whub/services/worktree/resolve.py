"""Resolve conventional task worktree locations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import shlex

from whub.core.remote import run_ssh_command
from whub.models import Host, Manifest, RemoteResource, SymlinkResource
from whub.services.errors import ServiceError
from whub.services.task.project import load_project_task


LOCAL_WORKTREE_ROOT = Path("projects/worktrees")


@dataclass(frozen=True)
class ResolvedProjectWorktree:
    """One conventional Task worktree and its owning resource."""

    project: str
    task_id: str
    branch: str
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


def _worktree_name(project: str, task_id: str) -> str:
    return f"{project}-{task_id.removeprefix('TASK-')}"


def _require_worktree_resource(
    manifest: Manifest, project: str
) -> SymlinkResource | RemoteResource:
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    resource = resolved_project.resource
    if resource is None:
        raise ServiceError(f"project has no resource: {project}")
    if resource.git is None or resource.git.branch is None:
        raise ServiceError(f"worktree parent has no git branch declaration: {project}")
    return resource


def _resolve_location(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> tuple[Path | str, Path | str, Host | None]:
    resource = _require_worktree_resource(manifest, project)
    name = _worktree_name(project, task_id)
    if isinstance(resource, SymlinkResource):
        return Path(resource.source), workspace_root / LOCAL_WORKTREE_ROOT / name, None
    if isinstance(resource, RemoteResource):
        host = manifest.hosts[resource.host]
        return (
            str(PurePosixPath(host.mount_root) / resource.path),
            str(PurePosixPath(host.mount_root) / host.worktree_root / name),
            host,
        )
    raise AssertionError(f"unsupported resource: {resource!r}")


def _require_destination(destination: Path | str, host: Host | None, project: str, task_id: str) -> None:
    if host is None:
        assert isinstance(destination, Path)
        exists = destination.is_dir()
    else:
        assert isinstance(destination, str)
        result = run_ssh_command(host, f"test -d {shlex.quote(destination)}")
        exists = result.returncode == 0
    if not exists:
        raise ServiceError(f"worktree not found: {project}/{task_id}")


def resolve_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> ResolvedProjectWorktree:
    """Load TASK and resolve its conventional worktree when it exists."""
    task = load_project_task(manifest, project, task_id).task
    resource = _require_worktree_resource(manifest, project)
    assert resource.git is not None and resource.git.branch is not None
    parent, destination, host = _resolve_location(manifest, workspace_root, project, task.id)
    _require_destination(destination, host, project, task.id)
    return ResolvedProjectWorktree(
        project=project,
        task_id=task.id,
        branch=f"tasks/{task.id.removeprefix('TASK-')}",
        parent=parent,
        destination=destination,
        base_branch=resource.git.branch,
        host=host,
    )
