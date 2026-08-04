"""Manifest models and loader — Pydantic model is SSOT for the schema."""

from __future__ import annotations
from collections import Counter
from pathlib import Path, PurePosixPath
from posixpath import normpath
from typing import Annotated, Literal
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ManifestError(Exception):
    """Raised when the manifest cannot be loaded or validated."""


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Host(SchemaModel):
    hostname: str
    user: str
    port: int = 22
    identity_file: str
    mount_root: str
    auto_mount: bool = True

    @field_validator("mount_root")
    @classmethod
    def _validate_mount_root(cls, value: str) -> str:
        if value.startswith("~") or not PurePosixPath(value).is_absolute():
            raise ValueError("mount_root must be an absolute path without '~'")
        return normpath(value)


class GitInfo(SchemaModel):
    url: str
    branch: str | None = None


class BaseResource(SchemaModel):
    git: GitInfo | None = None
    codegraph: bool = False
    status: bool = True


def _check_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("path must be relative")
    # Attachment paths must stay inside their root without resolving symlinks.
    if ".." in path.parts:
        raise ValueError("path must not escape its root")
    return value


RelativePath = Annotated[str, AfterValidator(_check_relative_path)]


# ── Local ─────────────────────────────────────────────────────────────────────────────────
class SymlinkResource(BaseResource):
    type: Literal["symlink"]
    workspace_path: RelativePath
    source: str
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
    # mount_rootの前置を各resourceへ重複させないため相対で持つ
    path: RelativePath
    workspace_path: RelativePath

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

        for project in self.projects:
            resource = project.resource
            if not isinstance(resource, RemoteResource):
                continue
            if resource.host not in self.hosts:
                raise ValueError(
                    f"project '{project.name}' references unknown host "
                    f"'{resource.host}'"
                )
        return self

    def resolve_project(self, name: str) -> Project | None:
        return next(
            (project for project in self.projects if project.name == name), None
        )
