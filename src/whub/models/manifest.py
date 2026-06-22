"""Manifest models and loader — Pydantic model is SSOT for the schema (see ADR-0004)."""
from __future__ import annotations
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    name: str
    git: GitInfo | None = None
    boot: bool = False

class SymlinkResource(BaseResource):
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
    host: str
    path: str

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        # Remote paths are interpreted by a POSIX shell on the destination host.
        if value.startswith("~") or not PurePosixPath(value).is_absolute():
            raise ValueError("remote path must be an absolute path without '~'")
        return value

class Resources(SchemaModel):
    symlinks: list[SymlinkResource] = Field(default_factory=list)
    remotes: list[RemoteResource] = Field(default_factory=list)

class Manifest(SchemaModel):
    version: Literal["1"] = "1"
    hosts: dict[str, Host] = Field(default_factory=dict)
    resources: Resources = Field(default_factory=Resources)
    root: Path = Path(".")

    @property
    def all_resources(self) -> tuple[SymlinkResource | RemoteResource, ...]:
        return (*self.resources.symlinks, *self.resources.remotes)

    @model_validator(mode="after")
    def _validate_resources(self) -> Manifest:
        names = [resource.name for resource in self.all_resources]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate resource names: {', '.join(duplicates)}")

        for resource in self.resources.remotes:
            if resource.host not in self.hosts:
                raise ValueError(
                    f"resource '{resource.name}' references unknown host "
                    f"'{resource.host}'"
                )
        return self

    def resolve_path(self, relative: str) -> Path:
        return self.root / relative

def load_manifest() -> Manifest:
    text = MANIFEST_PATH.read_text()
    data = yaml.safe_load(text)
    m = Manifest.model_validate(data)
    m.root = Path.cwd()
    return m

def resource_names(ctx, param, incomplete: str) -> list[str]:
    del ctx, param
    try:
        resources = load_manifest().all_resources
    except Exception:
        return []
    return [
        resource.name
        for resource in resources
        if resource.name.startswith(incomplete)
    ]

def host_names(ctx, param, incomplete: str) -> list[str]:
    del ctx, param
    try:
        hosts = load_manifest().hosts
    except Exception:
        return []
    return [name for name in hosts if name.startswith(incomplete)]
