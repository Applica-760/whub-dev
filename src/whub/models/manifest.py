"""Manifest models and loader — Pydantic model is SSOT for the schema (see ADR-0004)."""

from __future__ import annotations
from pathlib import Path
from typing import Annotated, Literal
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

MANIFEST_PATH = Path(".whub/manifest.yaml")

class Host(BaseModel):
    hostname: str
    user: str
    port: int = 22
    identity_file: str
    auto_mount: bool = True

class GitInfo(BaseModel):
    url: str
    branch: str | None = None

class BaseResource(BaseModel):
    name: str
    path: str
    git: GitInfo | None = None
    boot: bool = False

class SymlinkResource(BaseResource):
    type: Literal["symlink"]
    source: str

class MountResource(BaseResource):
    type: Literal["mount"]
    host: str
    remote_path: str

Resource = Annotated[SymlinkResource | MountResource, Field(discriminator="type")]

class Manifest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    version: str = "1"
    hosts: dict[str, Host] = Field(default_factory=dict)
    resources: list[Resource] = Field(default_factory=list)
    root: Path = Path(".")

    @model_validator(mode="after")
    def _check_host_refs(self):
        host_keys = set(self.hosts)
        for r in self.resources:
            if isinstance(r, MountResource) and r.host not in host_keys:
                raise ValueError(f"resource '{r.name}' references unknown host '{r.host}'")
        return self

    def resolve_path(self, relative: str) -> Path:
        # Normalize without following symlinks to catch ../../../ traversal
        combined = (self.root / relative)
        normalized = combined.resolve(strict=False) if ".." in relative else combined
        if ".." in relative and not normalized.is_relative_to(self.root.resolve()):
            raise ValueError(f"path escapes workspace root: {relative}")
        return combined

def load_manifest() -> Manifest:
    text = MANIFEST_PATH.read_text()
    data = yaml.safe_load(text)
    m = Manifest.model_validate(data)
    m.root = Path.cwd()
    return m
