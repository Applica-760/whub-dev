"""Manifest loading and workspace-specific resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml
from pydantic import ValidationError

from whub.core.context import WhubContext, current_context
from whub.models.manifest import (
    Host,
    Manifest,
    ManifestError,
    Project,
    RemoteResource,
    Resource,
)


@dataclass(frozen=True)
class ResolvedManifest:
    """A pure manifest bound to an explicit workspace root."""

    schema: Manifest
    workspace_root: Path

    @property
    def hosts(self) -> dict[str, Host]:
        return self.schema.hosts

    @property
    def projects(self) -> list[Project]:
        return self.schema.projects

    def resolve_project(self, name: str) -> Project | None:
        return self.schema.resolve_project(name)

    def workspace_path(self, resource: Resource) -> Path:
        legacy = getattr(resource, "_resolved_workspace_path", None)
        return legacy if legacy is not None else self.workspace_root / resource.workspace_path

    def remote_host(self, resource: RemoteResource) -> Host:
        legacy = getattr(resource, "_resolved_host", None)
        return legacy if legacy is not None else self.hosts[resource.host]

    def remote_path(self, resource: RemoteResource) -> str:
        return str(PurePosixPath(self.remote_host(resource).mount_root) / resource.path)


def resolve_manifest(manifest: Manifest, workspace_root: Path) -> ResolvedManifest:
    """Bind a pure Manifest schema to an explicit workspace root."""
    return ResolvedManifest(schema=manifest, workspace_root=workspace_root)


def load_manifest(context: WhubContext | None = None) -> ResolvedManifest:
    """Load and resolve the active context's manifest."""
    context = context or current_context()
    path = context.manifest_path
    try:
        text = context.read_manifest_text()
    except FileNotFoundError as error:
        raise ManifestError(f"manifest.yaml not found: {path}") from error
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ManifestError(f"invalid manifest YAML: {path}: {error}") from error
    try:
        schema = Manifest.model_validate(data)
    except ValidationError as error:
        raise ManifestError(f"invalid manifest: {path}: {error}") from error
    return resolve_manifest(schema, context.workspace_root)
