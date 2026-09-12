"""Resolve conventional Issue worktree locations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import shlex

from whub.core.remote import run_ssh_command
from whub.models import Host, Manifest, RemoteResource, SymlinkResource
from whub.services.errors import ServiceError


LOCAL_WORKTREE_ROOT = Path("projects/worktrees")


@dataclass(frozen=True)
class ResolvedProjectWorktree:
    """One conventional Task worktree and its owning resource."""

    project: str
    issue_number: int
    branch: str
    repository_url: str
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


def resolve_worktree(
    manifest: Manifest, workspace_root: Path, project: str, issue_number: int
) -> ResolvedProjectWorktree:
    """Derive one Issue worktree location without reading Task records."""
    if issue_number < 1:
        raise ServiceError("issue number must be positive")
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    resource = resolved_project.resource
    if resource is None:
        raise ServiceError(f"project has no resource: {project}")
    if resource.git is None or not resource.git.url or resource.git.branch is None:
        raise ServiceError(f"worktree requires git.url and git.branch: {project}")
    assert resource.git is not None and resource.git.branch is not None
    name = f"{project}-{issue_number}"
    if isinstance(resource, SymlinkResource):
        parent, destination, host = (
            Path(resource.source),
            workspace_root / LOCAL_WORKTREE_ROOT / name,
            None,
        )
    elif isinstance(resource, RemoteResource):
        host = manifest.hosts[resource.host]
        parent, destination = (
            str(PurePosixPath(host.mount_root) / resource.path),
            str(PurePosixPath(host.mount_root) / host.worktree_root / name),
        )
    else:
        raise AssertionError(f"unsupported resource: {resource!r}")
    return ResolvedProjectWorktree(
        project=project,
        issue_number=issue_number,
        branch=f"issue/{issue_number}",
        repository_url=resource.git.url,
        parent=parent,
        destination=destination,
        base_branch=resource.git.branch,
        host=host,
    )


def worktree_exists(worktree: ResolvedProjectWorktree) -> bool:
    """Return whether WORKTREE's conventional destination is a directory."""
    if worktree.host is None:
        assert isinstance(worktree.destination, Path)
        return worktree.destination.is_dir()
    assert isinstance(worktree.destination, str)
    result = run_ssh_command(
        worktree.host, f"test -d {shlex.quote(worktree.destination)}"
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = result.stderr.strip() or f"exit status {result.returncode}"
    raise ServiceError(f"worktree existence check failed: {detail}")


def resolve_conventional_worktree(
    manifest: Manifest, workspace_root: Path, project: str, issue_number: int
) -> ResolvedProjectWorktree:
    """Resolve an existing conventional Issue worktree."""
    worktree = resolve_worktree(manifest, workspace_root, project, issue_number)
    if not worktree_exists(worktree):
        raise ServiceError(f"worktree not found: {project}/{issue_number}")
    return worktree
