"""Project content resolution shared by whub services."""
from __future__ import annotations

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
