"""Project content resolution shared by whub services."""

from __future__ import annotations

from pathlib import Path

from whub.core.health import probe_directory_readable
from whub.models import Manifest, RemoteResource, SymlinkResource
from whub.services.errors import ServiceError


def resolve_project_content_resource(
    manifest: Manifest,
    project: str,
) -> SymlinkResource | RemoteResource:
    """Resolve a Project's declared resource."""
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    if resolved_project.resource is not None:
        return resolved_project.resource
    raise ServiceError(f"project has no resource: {project}")


def resolve_project_content_root(manifest: Manifest, project: str) -> Path:
    """Resolve an available local or mounted Project content root."""
    resource = resolve_project_content_resource(manifest, project)
    root = (
        Path(resource.source).expanduser()
        if isinstance(resource, SymlinkResource)
        else resource._resolved_workspace_path
    )
    if not root.is_dir():
        raise ServiceError(f"project resource is not available: {project}")
    if detail := probe_directory_readable(root):
        recovery = (
            "allow Network Volumes access for this app, then remount"
            if isinstance(resource, RemoteResource)
            else "check local filesystem permissions"
        )
        raise ServiceError(
            f"project resource is unreadable: {project}: {detail}; {recovery}"
        )
    return root
