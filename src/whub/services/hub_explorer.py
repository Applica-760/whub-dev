"""Read-only directory browsing rooted at the workspace hub."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from typing import Literal

from pydantic import BaseModel

from whub.core.git import run_git
from whub.services.errors import NotFoundError, ServiceError
from whub.services.manifest import ResolvedManifest


class HubEntry(BaseModel):
    """One visible entry in a Hub Explorer directory."""

    name: str
    path: str
    type: Literal["directory", "file"]
    expandable: bool
    changed: bool = False


class HubFile(BaseModel):
    """Displayable text file state."""

    path: str
    content: str | None
    state: Literal["text", "binary", "unreadable"]
    diff: str = ""


def list_hub_directory(
    manifest: ResolvedManifest,
    root: Path,
    relative_path: str = "",
) -> list[HubEntry]:
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
                changed=_path_has_changes(manifest, root, path),
            )
        )
    return entries


def read_hub_file(
    manifest: ResolvedManifest,
    root: Path,
    relative_path: str,
) -> HubFile:
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
        return HubFile(
            path=relative_path,
            content=content.decode(),
            state="text",
            diff=_file_diff(manifest, root, relative_path, resolved),
        )
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


def _git_context(
    manifest: ResolvedManifest,
    root: Path,
    relative_path: str,
) -> tuple[Path, str] | None:
    parts = PurePosixPath(relative_path).parts
    if not parts:
        return None
    if parts[0] == "whub-dev":
        project = manifest.resolve_project("whub-dev")
    else:
        return None
    if project is None or project.resource is None or project.resource.git is None:
        return None
    branch = project.resource.git.branch
    if branch is None:
        return None
    target, _ = _resolve_logical_path(root, relative_path)
    result = run_git(target.parent if target.is_file() else target, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()), branch


def _path_has_changes(
    manifest: ResolvedManifest,
    root: Path,
    relative_path: str,
) -> bool:
    context = _git_context(manifest, root, relative_path)
    if context is None:
        return False
    repository, branch = context
    target, _ = _resolve_logical_path(root, relative_path)
    try:
        repo_path = str(target.resolve().relative_to(repository))
    except ValueError:
        return False
    changed = run_git(repository, "diff", "--quiet", branch, "--", repo_path)
    if changed.returncode == 1:
        return True
    if changed.returncode != 0:
        raise ServiceError("git diff failed: " + _process_detail(changed))
    untracked = run_git(
        repository,
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        repo_path,
    )
    if untracked.returncode != 0:
        raise ServiceError("git ls-files failed: " + _process_detail(untracked))
    return bool(untracked.stdout.strip())


def _file_diff(
    manifest: ResolvedManifest,
    root: Path,
    relative_path: str,
    target: Path,
) -> str:
    context = _git_context(manifest, root, relative_path)
    if context is None:
        return ""
    repository, branch = context
    try:
        repo_path = str(target.relative_to(repository))
    except ValueError:
        return ""
    if _path_has_changes(manifest, root, relative_path):
        untracked = run_git(
            repository,
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            repo_path,
        )
        if untracked.stdout.strip():
            result = run_git(
                repository,
                "diff",
                "--no-index",
                "--no-ext-diff",
                "--unified=3",
                "--",
                "/dev/null",
                repo_path,
            )
        else:
            result = run_git(
                repository,
                "diff",
                "--no-ext-diff",
                "--unified=3",
                branch,
                "--",
                repo_path,
            )
        if result.returncode not in (0, 1):
            raise ServiceError("git diff failed: " + _process_detail(result))
        return result.stdout
    return ""


def _process_detail(result: subprocess.CompletedProcess[str]) -> str:
    return result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
