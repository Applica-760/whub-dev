"""Worktree parent eligibility."""

from __future__ import annotations

from whub.models import Manifest, SymlinkResource
from whub.services.errors import ServiceError


def require_worktree_parent(manifest: Manifest, project: str) -> SymlinkResource:
    """Resolve a Project eligible to own a local Git worktree."""
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    resource = resolved_project.resource
    if resource is None:
        raise ServiceError(f"project has no resource: {project}")
    if not isinstance(resource, SymlinkResource):
        raise ServiceError(f"not a local resource: {project}")
    if resource.git is None:
        raise ServiceError(f"worktree parent has no git declaration: {project}")
    return resource
