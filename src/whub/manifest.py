"""Manifest loader — Pydantic model is SSOT for the schema (see ADR-0004)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator


class Host(BaseModel):
    hostname: str
    user: str
    port: int = 22
    identity_file: str


class GitInfo(BaseModel):
    url: str
    branch: str | None = None


class Resource(BaseModel):
    name: str
    path: str
    type: Literal["mount", "symlink"]

    # mount
    host: str | None = None
    remote_path: str | None = None

    # symlink
    source: str | None = None
    # common optional
    git: GitInfo | None = None
    agent_rules: bool = False

    @model_validator(mode="after")
    def _check_type_fields(self):
        if self.type == "mount":
            if not self.host or not self.remote_path:
                raise ValueError(f"resource '{self.name}': mount requires host and remote_path")
        elif self.type == "symlink":
            if not self.source:
                raise ValueError(f"resource '{self.name}': symlink requires source")
        return self


class Manifest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    version: str = "1"
    hosts: dict[str, Host] | None = None
    resources: list[Resource] = []
    root: Path = Path(".")

    @model_validator(mode="after")
    def _check_host_refs(self):
        host_keys = set(self.hosts or {})
        for r in self.resources:
            if r.type == "mount" and r.host not in host_keys:
                raise ValueError(f"resource '{r.name}' references unknown host '{r.host}'")
        return self

    def resolve_path(self, relative: str) -> Path:
        return self.root / relative


def load_manifest(path: Path | None = None) -> Manifest:
    if path is None:
        path = Path("manifest.yaml")
    path = path.resolve()
    text = path.read_text()
    data = yaml.safe_load(text)
    m = Manifest.model_validate(data)
    m.root = path.parent
    return m
