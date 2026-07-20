"""Project content resolution shared by whub services."""
from __future__ import annotations

from pathlib import Path

from whub.models import (
    Manifest,
    RemoteResource,
    SymlinkResource,
    workspace_hub_resource,
)
from whub.services.errors import ServiceError


def resolve_project_content_resource(
    manifest: Manifest,
    project: str,
) -> SymlinkResource | RemoteResource:
    """Resolve a Project resource, including workspace-hub's synthetic resource."""
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    if resolved_project.resource is not None:
        return resolved_project.resource
    if resolved_project.name == "workspace-hub":
        return workspace_hub_resource()
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
    return root
