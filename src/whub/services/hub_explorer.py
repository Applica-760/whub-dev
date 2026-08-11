"""Read-only directory browsing rooted at the workspace hub."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import stat
from typing import Literal

from pydantic import BaseModel

from whub.services.errors import NotFoundError


class HubEntry(BaseModel):
    """One visible entry in a Hub Explorer directory."""

    name: str
    path: str
    type: Literal["directory", "file"]
    expandable: bool


class HubFile(BaseModel):
    """Displayable text file state."""

    path: str
    content: str | None
    state: Literal["text", "binary", "unreadable"]


def list_hub_directory(root: Path, relative_path: str = "") -> list[HubEntry]:
    """List one logical Hub directory, excluding Git metadata."""
    directory, parts = _resolve_logical_path(root, relative_path)
    if not directory.is_dir() or _contains_git(directory.resolve()):
        raise NotFoundError(f"hub directory not found: {relative_path}")
    ancestors = _ancestor_targets(root, parts)
    entries: list[HubEntry] = []
    for entry in sorted(
        directory.iterdir(), key=lambda item: (not item.is_dir(), item.name)
    ):
        if entry.name == ".git":
            continue
        try:
            target = entry.resolve()
            directory_entry = entry.is_dir()
        except OSError:
            target = None
            directory_entry = False
        if target is not None and _contains_git(target):
            continue
        path = "/".join((*parts, entry.name))
        entries.append(
            HubEntry(
                name=entry.name,
                path=path,
                type="directory" if directory_entry else "file",
                expandable=directory_entry and target not in ancestors,
            )
        )
    return entries


def read_hub_file(root: Path, relative_path: str) -> HubFile:
    """Read one logical Hub text file without exposing Git metadata."""
    target, _ = _resolve_logical_path(root, relative_path)
    try:
        resolved = target.resolve()
    except OSError as error:
        raise NotFoundError(f"hub file not found: {relative_path}") from error
    if _contains_git(resolved) or not resolved.is_file():
        raise NotFoundError(f"hub file not found: {relative_path}")
    try:
        descriptor = os.open(resolved, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                return HubFile(path=relative_path, content=None, state="unreadable")
            content = file.read()
    except OSError:
        return HubFile(path=relative_path, content=None, state="unreadable")
    if b"\0" in content:
        return HubFile(path=relative_path, content=None, state="binary")
    try:
        return HubFile(path=relative_path, content=content.decode(), state="text")
    except UnicodeDecodeError:
        return HubFile(path=relative_path, content=None, state="binary")


def _resolve_logical_path(
    root: Path, relative_path: str
) -> tuple[Path, tuple[str, ...]]:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or any(part in (".", "..") for part in path.parts):
        raise NotFoundError(f"hub path not found: {relative_path}")
    return root.joinpath(*path.parts), path.parts


def _ancestor_targets(root: Path, parts: tuple[str, ...]) -> set[Path]:
    ancestors = {root.resolve()}
    current = root
    for part in parts:
        current /= part
        ancestors.add(current.resolve())
    return ancestors


def _contains_git(path: Path) -> bool:
    return ".git" in path.parts
