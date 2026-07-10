"""Inbox note creation shared by web adapters."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from whub.models import Manifest
from whub.services.errors import ServiceError


_INVALID_TITLE_CHARACTERS = frozenset('/\\:*?"<>|')


def _validate_input(title: str, body: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise ServiceError("inbox title is required")
    if any(
        character in _INVALID_TITLE_CHARACTERS
        or ord(character) < 32
        or ord(character) == 127
        for character in normalized
    ):
        raise ServiceError("inbox title contains invalid filename characters")
    if not body.strip():
        raise ServiceError("inbox body is required")
    return normalized


def _resolve_vault_path(manifest: Manifest) -> Path:
    project = manifest.resolve_project("vault")
    if project is None:
        raise ServiceError("vault project is not defined")
    if project.resource is None:
        raise ServiceError("vault project has no resource")

    path = project.resource._resolved_workspace_path
    if not path.is_dir():
        raise ServiceError(f"vault workspace path is not available: {path}")
    return path


def create_inbox_note(manifest: Manifest, title: str, body: str) -> Path:
    """Create an inbox note and return its path."""
    normalized_title = _validate_input(title, body)
    inbox_dir = _resolve_vault_path(manifest) / "inbox"
    path = inbox_dir / f"{datetime.now():%Y%m%d_%H%M}_{normalized_title}.md"
    if path.exists():
        raise ServiceError(f"inbox note already exists: {path.name}")
    path.write_text(body, encoding="utf-8")
    return path
