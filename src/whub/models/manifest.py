"""Manifest models and loader — Pydantic model is SSOT for the schema."""
from __future__ import annotations
from typing import Annotated, Literal
from pathlib import Path
from pathlib import PurePosixPath
import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

MANIFEST_PATH = Path(".whub/manifest.yaml")

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
    boot: bool = False

class SymlinkResource(BaseResource):
    type: Literal["symlink"]
    workspace_path: str
    source: str

    @field_validator("workspace_path")
    @classmethod
    def _validate_workspace_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute():
            raise ValueError("workspace_path must be relative")
        # Attachment paths must stay inside workspace-hub without resolving symlinks.
        if ".." in path.parts:
            raise ValueError("workspace_path must not escape workspace root")
        return value

    @field_validator("source")
    @classmethod
    def _validate_source(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("source must be an absolute path")
        return value

class RemoteResource(BaseResource):
    type: Literal["remote"]
    host: str
    path: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        # Remote paths are interpreted by a POSIX shell on the destination host.
        if value.startswith("~") or not PurePosixPath(value).is_absolute():
            raise ValueError("remote path must be an absolute path without '~'")
        return value

Resource = Annotated[SymlinkResource | RemoteResource, Field(discriminator="type")]

class Project(SchemaModel):
    name: str
    resource: Resource | None = None

class Manifest(SchemaModel):
    version: Literal["2"] = "2"
    hosts: dict[str, Host] = Field(default_factory=dict)
    projects: list[Project] = Field(default_factory=list)
    _root: Path = PrivateAttr(default=Path("."))

    @model_validator(mode="after")
    def _validate_projects(self) -> Manifest:
        names = [project.name for project in self.projects]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate project names: {', '.join(duplicates)}")

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

    @property
    def workspace_root(self) -> Path:
        return self._root

    def resolve_path(self, relative: str) -> Path:
        return self._root / relative

    def resolve_project(self, name: str) -> Project | None:
        return next((project for project in self.projects if project.name == name), None)

def load_manifest() -> Manifest:
    text = MANIFEST_PATH.read_text()
    data = yaml.safe_load(text)
    m = Manifest.model_validate(data)
    m._root = Path.cwd()
    return m

def project_names(ctx, param, incomplete: str) -> list[str]:
    del ctx, param
    try:
        projects = load_manifest().projects
    except Exception:
        return []
    return [
        project.name
        for project in projects
        if project.name.startswith(incomplete)
    ]

def host_names(ctx, param, incomplete: str) -> list[str]:
    del ctx, param
    try:
        hosts = load_manifest().hosts
    except Exception:
        return []
    return [name for name in hosts if name.startswith(incomplete)]
