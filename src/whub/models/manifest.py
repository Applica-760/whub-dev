"""Manifest models and loader — Pydantic model is SSOT for the schema."""

from __future__ import annotations
from collections import Counter
from typing import Annotated, Literal
from pathlib import Path
from pathlib import PurePosixPath
import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)
from pydantic import ValidationError

from whub.core.context import WhubContext, current_context


class ManifestError(Exception):
    """Raised when the manifest cannot be loaded or validated."""


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Host(SchemaModel):
    hostname: str
    user: str
    port: int = 22
    identity_file: str


class GitInfo(SchemaModel):
    url: str
    branch: str | None = None


class BaseResource(SchemaModel):
    git: GitInfo | None = None
    codegraph: bool = False
    status: bool = True


def _check_workspace_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("workspace_path must be relative")
    # Attachment paths must stay inside the workspace root without resolving symlinks.
    if ".." in path.parts:
        raise ValueError("workspace_path must not escape workspace root")
    return value


WorkspacePath = Annotated[str, AfterValidator(_check_workspace_path)]


# ── Local ─────────────────────────────────────────────────────────────────────────────────
class SymlinkResource(BaseResource):
    type: Literal["symlink"]
    workspace_path: WorkspacePath
    source: str
    _resolved_workspace_path: Path = PrivateAttr()

    @field_validator("source")
    @classmethod
    def _validate_source(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("source must be an absolute path")
        return value


# ── Remote ─────────────────────────────────────────────────────────────────────────────────
class RemoteResource(BaseResource):
    type: Literal["remote"]
    host: str
    path: str
    workspace_path: WorkspacePath
    mount: bool = True
    _resolved_host: Host = PrivateAttr()
    _resolved_workspace_path: Path = PrivateAttr()

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if value.startswith("~") or not PurePosixPath(value).is_absolute():
            raise ValueError("remote path must be an absolute path without '~'")
        return value


# ── Project ─────────────────────────────────────────────────────────────────────────────────
Resource = Annotated[SymlinkResource | RemoteResource, Field(discriminator="type")]


class Project(SchemaModel):
    name: str
    resource: Resource | None = None


# ── Manifest ─────────────────────────────────────────────────────────────────────────────────
class Manifest(SchemaModel):
    version: Literal["2"] = "2"
    hosts: dict[str, Host] = Field(default_factory=dict)
    projects: list[Project] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_projects(self) -> Manifest:
        name_counts = Counter(project.name for project in self.projects)
        duplicates = sorted(name for name, count in name_counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate project names: {', '.join(duplicates)}")

        # 重複するとmountのmountpoint衝突、fetchのパス解決が先勝ちになる
        path_counts = Counter(
            project.resource.workspace_path
            for project in self.projects
            if project.resource is not None
        )
        duplicate_paths = sorted(
            path for path, count in path_counts.items() if count > 1
        )
        if duplicate_paths:
            raise ValueError(f"duplicate workspace_path: {', '.join(duplicate_paths)}")

        root = current_context().workspace_root
        for project in self.projects:
            resource = project.resource
            if isinstance(resource, SymlinkResource):
                resource._resolved_workspace_path = root / resource.workspace_path
                continue
            if not isinstance(resource, RemoteResource):
                continue
            if resource.host not in self.hosts:
                raise ValueError(
                    f"project '{project.name}' references unknown host "
                    f"'{resource.host}'"
                )
            resource._resolved_host = self.hosts[resource.host]
            resource._resolved_workspace_path = root / resource.workspace_path
        return self

    def resolve_project(self, name: str) -> Project | None:
        return next(
            (project for project in self.projects if project.name == name), None
        )


def load_manifest(context: WhubContext | None = None) -> Manifest:
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
        return Manifest.model_validate(data)
    except ValidationError as error:
        raise ManifestError(f"invalid manifest: {path}: {error}") from error


def project_names(ctx, param, incomplete: str) -> list[str]:
    del ctx, param
    try:
        projects = load_manifest().projects
    except Exception:
        return []
    return [project.name for project in projects if project.name.startswith(incomplete)]
