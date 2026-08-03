"""Read Git Explorer files and diffs from a registered task worktree."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.worktree.git import process_detail, run_git
from whub.services.worktree.operation import resolve_project_worktree


@dataclass(frozen=True)
class ChangedFile:
    """One non-ignored file in a task worktree and its optional Git status."""

    path: str
    status: str
    previous_path: str | None = None


@dataclass(frozen=True)
class WorktreeDiff:
    """The display inputs for one current worktree file."""

    path: str
    content: str | None
    diff: str
    state: str


def list_changed_files(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
) -> list[ChangedFile]:
    """Return every tracked or non-ignored file with its base-branch status."""
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    paths = _list_worktree_paths(worktree.destination)
    changed = _list_changed_files(worktree.destination, worktree.base_branch)
    changed_by_path = {item.path: item for item in changed}
    untracked = _list_untracked_paths(worktree.destination)
    return [
        changed_by_path.get(path, ChangedFile(path=path, status="A" if path in untracked else ""))
        for path in paths
    ]


def read_changed_file_diff(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
    path: str,
) -> WorktreeDiff:
    """Return PATH's current text and unified diff when it is displayable."""
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    paths = _list_worktree_paths(worktree.destination)
    if path not in paths:
        raise NotFoundError(f"worktree file not found: {path}")
    content, state = _read_worktree_text(worktree.destination, path)
    if state != "text":
        return WorktreeDiff(path=path, content=None, diff="", state=state)
    if path in _list_untracked_paths(worktree.destination):
        result = run_git(
            worktree.destination,
            "diff",
            "--no-index",
            "--no-ext-diff",
            "--unified=3",
            "--",
            "/dev/null",
            path,
        )
        if result.returncode not in (0, 1):
            raise ServiceError("git diff failed: " + process_detail(result))
        return WorktreeDiff(path=path, content=content, diff=result.stdout, state=state)
    result = run_git(
        worktree.destination,
        "diff",
        "--no-ext-diff",
        "--unified=3",
        worktree.base_branch,
        "--",
        path,
    )
    if result.returncode != 0:
        raise ServiceError("git diff failed: " + process_detail(result))
    return WorktreeDiff(path=path, content=content, diff=result.stdout, state=state)


def _list_changed_files(destination: Path, base_branch: str) -> list[ChangedFile]:
    result = run_git(
        destination,
        "diff",
        "--name-status",
        "-z",
        base_branch,
    )
    if result.returncode != 0:
        raise ServiceError("git diff failed: " + process_detail(result))
    return _parse_changed_files(result.stdout)


def _list_worktree_paths(destination: Path) -> list[str]:
    result = run_git(
        destination,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    if result.returncode != 0:
        raise ServiceError("git ls-files failed: " + process_detail(result))
    return sorted(path for path in result.stdout.split("\0") if path)


def _list_untracked_paths(destination: Path) -> set[str]:
    result = run_git(
        destination,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )
    if result.returncode != 0:
        raise ServiceError("git ls-files failed: " + process_detail(result))
    return {path for path in result.stdout.split("\0") if path}


def _read_worktree_text(destination: Path, path: str) -> tuple[str | None, str]:
    target = destination / path
    try:
        if not stat.S_ISREG(target.lstat().st_mode):
            return None, "unreadable"
        descriptor = os.open(target, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except OSError:
        return None, "unreadable"
    try:
        with os.fdopen(descriptor, "rb") as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                return None, "unreadable"
            content = file.read()
    except OSError:
        return None, "unreadable"
    if b"\0" in content:
        return None, "binary"
    try:
        return content.decode(), "text"
    except UnicodeDecodeError:
        return None, "binary"


def _parse_changed_files(output: str) -> list[ChangedFile]:
    fields = iter(output.split("\0"))
    changed_files: list[ChangedFile] = []
    for status in fields:
        if not status:
            continue
        try:
            if status.startswith(("R", "C")):
                previous_path = next(fields)
                path = next(fields)
            else:
                previous_path = None
                path = next(fields)
        except StopIteration as error:
            raise ServiceError(
                "git diff returned invalid name-status output"
            ) from error
        changed_files.append(
            ChangedFile(path=path, status=status[0], previous_path=previous_path)
        )
    return changed_files
