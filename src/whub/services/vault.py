"""Vault read-only browsing shared by web adapters."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError


class VaultNode(BaseModel):
    """A directory or markdown file in the vault tree."""

    name: str
    path: str
    type: Literal["directory", "file"]
    children: list[VaultNode] = []


def resolve_vault_path(manifest: Manifest) -> Path:
    """Return the vault workspace path or raise if unavailable."""
    project = manifest.resolve_project("vault")
    if project is None:
        raise ServiceError("vault project is not defined")
    if project.resource is None:
        raise ServiceError("vault project has no resource")

    path = project.resource._resolved_workspace_path
    if not path.is_dir():
        raise ServiceError(f"vault workspace path is not available: {path}")
    return path


def list_vault_tree(manifest: Manifest) -> list[VaultNode]:
    """Return the vault's .md files as a nested tree of nodes."""
    root = resolve_vault_path(manifest)
    return _scan_directory(root, root)


def read_vault_note(manifest: Manifest, relative_path: str) -> str:
    """Return the raw content of a vault note."""
    root = resolve_vault_path(manifest)
    target = (root / relative_path).resolve()
    if (
        not target.is_relative_to(root.resolve())
        or target.suffix != ".md"
        or not target.is_file()
    ):
        raise NotFoundError(f"vault note not found: {relative_path}")
    return target.read_text(encoding="utf-8")


def _scan_directory(directory: Path, root: Path) -> list[VaultNode]:
    nodes: list[VaultNode] = []
    entries = sorted(directory.iterdir(), key=lambda entry: (entry.is_file(), entry.name))
    for entry in entries:
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            children = _scan_directory(entry, root)
            if children:
                nodes.append(VaultNode(
                    name=entry.name,
                    path=str(entry.relative_to(root)),
                    type="directory",
                    children=children,
                ))
        elif entry.suffix == ".md":
            nodes.append(VaultNode(
                name=entry.name,
                path=str(entry.relative_to(root)),
                type="file",
            ))
    return nodes
