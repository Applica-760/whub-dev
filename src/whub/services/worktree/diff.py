"""Read PR changes from a registered task worktree."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.worktree.git import process_detail, run_git
from whub.services.worktree.operation import resolve_project_worktree


@dataclass(frozen=True)
class ChangedFile:
    """One path changed between a task branch and its configured base branch."""

    path: str
    status: str
    previous_path: str | None = None


@dataclass(frozen=True)
class WorktreeDiff:
    """The unified diff for one changed file."""

    path: str
    content: str


def list_changed_files(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
) -> list[ChangedFile]:
    """Return files changed by TASK_ID from the configured base branch."""
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    result = run_git(
        worktree.destination,
        "diff",
        "--name-status",
        "-z",
        worktree.base_branch,
    )
    if result.returncode != 0:
        raise ServiceError("git diff failed: " + process_detail(result))
    return _parse_changed_files(result.stdout)


def read_changed_file_diff(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
    path: str,
) -> WorktreeDiff:
    """Return PATH's unified diff when it belongs to the task branch change set."""
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    changed_files = _list_changed_files(worktree.destination, worktree.base_branch)
    if path not in {item.path for item in changed_files}:
        raise NotFoundError(f"changed file not found: {path}")
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
    return WorktreeDiff(path=path, content=result.stdout)


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
