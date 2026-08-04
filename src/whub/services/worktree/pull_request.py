"""Create and merge pull requests for registered worktrees."""

from __future__ import annotations

import json
from pathlib import Path

from whub.models import Manifest
from whub.services.errors import ServiceError
from whub.services.worktree.github import run_gh
from whub.services.worktree.git import process_detail, run_git
from whub.services.worktree.lifecycle import remove_project_worktree
from whub.services.worktree.resolve import ResolvedProjectWorktree, resolve_project_worktree


_MERGE_METHODS = frozenset(("merge", "squash", "rebase"))


def _require_clean_worktree(worktree: ResolvedProjectWorktree) -> None:
    """Reject a worktree whose branch does not fully represent its contents."""
    status = run_git(
        worktree.destination, "status", "--porcelain", "--untracked-files=all"
    )
    if status.returncode != 0:
        raise ServiceError("git status failed: " + process_detail(status))
    if status.stdout.strip():
        raise ServiceError(
            f"worktree has uncommitted changes: {worktree.definition.workspace_path}"
        )


def create_project_pull_request(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> str:
    """Push a clean task branch and create or return its open GitHub PR."""
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    _require_clean_worktree(worktree)
    pushed = run_git(
        worktree.destination,
        "push",
        "--set-upstream",
        "origin",
        worktree.definition.branch,
    )
    if pushed.returncode != 0:
        raise ServiceError("git push failed: " + process_detail(pushed))
    existing = run_gh(
        worktree.destination,
        "pr",
        "list",
        "--head",
        worktree.definition.branch,
        "--base",
        worktree.base_branch,
        "--state",
        "open",
        "--json",
        "url",
        "--jq",
        ".[0].url",
    )
    if existing.returncode != 0:
        raise ServiceError("gh PR lookup failed: " + process_detail(existing))
    if existing.stdout.strip():
        return existing.stdout.strip()
    created = run_gh(
        worktree.destination,
        "pr",
        "create",
        "--base",
        worktree.base_branch,
        "--head",
        worktree.definition.branch,
        "--title",
        worktree.definition.task_id,
        "--body",
        "",
    )
    if created.returncode != 0:
        raise ServiceError("gh PR create failed: " + process_detail(created))
    return created.stdout.strip()


def merge_project_pull_request(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
    method: str,
) -> None:
    """Merge one open task PR, then remove its worktree only after confirmation."""
    if method not in _MERGE_METHODS:
        raise ServiceError(f"invalid merge method: {method}")
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    _require_clean_worktree(worktree)
    viewed = run_gh(
        worktree.destination,
        "pr",
        "list",
        "--head",
        worktree.definition.branch,
        "--base",
        worktree.base_branch,
        "--state",
        "open",
        "--json",
        "url,headRefOid",
    )
    if viewed.returncode != 0:
        raise ServiceError("gh PR lookup failed: " + process_detail(viewed))
    try:
        pull_requests = json.loads(viewed.stdout)
        if not isinstance(pull_requests, list):
            raise TypeError
        if not pull_requests:
            raise ServiceError(f"open pull request not found: {project}/{task_id}")
        if len(pull_requests) != 1:
            raise ServiceError(
                f"multiple open pull requests found: {project}/{task_id}"
            )
        pull_request = pull_requests[0]
        url = pull_request["url"]
        head_oid = pull_request["headRefOid"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ServiceError("gh PR lookup returned invalid data") from error
    merged = run_gh(
        worktree.destination,
        "pr",
        "merge",
        url,
        f"--{method}",
        "--match-head-commit",
        head_oid,
    )
    if merged.returncode != 0:
        raise ServiceError("gh PR merge failed: " + process_detail(merged))
    confirmed = run_gh(
        worktree.destination,
        "pr",
        "view",
        url,
        "--json",
        "state",
        "--jq",
        ".state",
    )
    if confirmed.returncode != 0:
        raise ServiceError("gh PR verification failed: " + process_detail(confirmed))
    if confirmed.stdout.strip() != "MERGED":
        raise ServiceError(f"pull request was not merged: {url}")
    try:
        remove_project_worktree(manifest, workspace_root, project, task_id)
    except ServiceError as error:
        raise ServiceError(f"pull request merged but cleanup failed: {error}") from error
