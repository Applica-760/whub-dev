"""Task worktree open and close operations."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from whub.core.github import github_repository, run_gh
from whub.core.git import run_git_at
from whub.core.tmux import TmuxSession
from whub.models import Manifest
from whub.services.agent.agent import (
    close_agent,
    open_agent,
    unchanged_generated_paths,
)
from whub.services.errors import ServiceError
from whub.services.worktree.resolve import (
    ResolvedProjectWorktree,
    resolve_conventional_worktree,
    resolve_worktree,
    worktree_exists,
)


def open_project_worktree(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    issue_number: int,
    auth_names: tuple[str, ...],
) -> TmuxSession:
    """Create one conventional worktree, then prepare and open its Agent."""
    worktree = resolve_worktree(manifest, workspace_root, project, issue_number)
    created_branch = False
    created_worktree = False
    try:
        if not worktree_exists(worktree):
            created_branch = _prepare_issue_branch(worktree)
            _add_worktree(worktree)
            created_worktree = True
        return open_agent(manifest, workspace_root, project, issue_number, auth_names)
    except (OSError, ServiceError) as error:
        try:
            if created_worktree:
                _rollback_open(worktree, created_branch)
            elif created_branch:
                _rollback_branch(worktree)
        except ServiceError as rollback_error:
            raise ServiceError(
                f"worktree open failed: {error}; rollback failed: {rollback_error}"
            ) from error
        raise


def close_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, issue_number: int
) -> str:
    """Clean Agent files, merge one Issue PR, then remove its worktree."""
    worktree = resolve_conventional_worktree(
        manifest, workspace_root, project, issue_number
    )
    _require_clean_worktree(manifest, workspace_root, worktree)
    close_agent(manifest, workspace_root, project, worktree.issue_number)
    url, head_oid = _push_and_create_pull_request(worktree)
    _require_gh(
        worktree,
        worktree.destination,
        "pr",
        "merge",
        url,
        "--merge",
        "--match-head-commit",
        head_oid,
    )
    state = _require_gh(
        worktree, worktree.destination, "pr", "view", url, "--json", "state", "--jq", ".state"
    )
    if state.stdout.strip() != "MERGED":
        raise ServiceError(f"pull request was not merged: {url}")
    try:
        _require_git(worktree, "worktree", "remove", str(worktree.destination))
    except (OSError, ServiceError) as error:
        raise ServiceError(
            f"pull request merged but cleanup failed: {error}"
        ) from error
    return url


def create_project_pull_request(
    manifest: Manifest, workspace_root: Path, project: str, issue_number: int
) -> str:
    """Push one clean Issue branch and create or return its pull request."""
    worktree = resolve_conventional_worktree(
        manifest, workspace_root, project, issue_number
    )
    _require_clean_worktree(manifest, workspace_root, worktree)
    url, _ = _push_and_create_pull_request(worktree)
    return url


def _push_and_create_pull_request(worktree: ResolvedProjectWorktree) -> tuple[str, str]:
    _require_git(worktree, "push", "--set-upstream", "origin", worktree.branch)
    head_oid = _require_git(worktree, "rev-parse", "HEAD").stdout.strip()
    if not head_oid:
        raise ServiceError("git rev-parse returned no HEAD")
    listed = _require_gh(
        worktree,
        worktree.destination,
        "pr",
        "list",
        "--head",
        worktree.branch,
        "--base",
        worktree.base_branch,
        "--state",
        "open",
        "--json",
        "url,headRefOid",
    )
    try:
        pull_requests = json.loads(listed.stdout)
        if not isinstance(pull_requests, list):
            raise TypeError
    except (TypeError, json.JSONDecodeError) as error:
        raise ServiceError("gh PR lookup returned invalid data") from error
    if len(pull_requests) > 1:
        raise ServiceError(
            f"multiple open pull requests found: {worktree.project}/{worktree.issue_number}"
        )
    if pull_requests:
        pull_request = pull_requests[0]
    else:
        created = _require_gh(
            worktree,
            worktree.destination,
            "pr",
            "create",
            "--base",
            worktree.base_branch,
            "--head",
            worktree.branch,
            "--title",
            f"#{worktree.issue_number}",
            "--body",
            "",
        )
        url = created.stdout.strip()
        if not url:
            raise ServiceError("gh PR create returned no URL")
        viewed = _require_gh(
            worktree,
            worktree.destination,
            "pr",
            "view",
            url,
            "--json",
            "url,headRefOid",
        )
        try:
            pull_request = json.loads(viewed.stdout)
        except json.JSONDecodeError as error:
            raise ServiceError("gh PR view returned invalid data") from error
    if not isinstance(pull_request, dict):
        raise ServiceError("gh PR lookup returned invalid data")
    url = pull_request.get("url")
    pr_head_oid = pull_request.get("headRefOid")
    if not isinstance(url, str) or not isinstance(pr_head_oid, str):
        raise ServiceError("gh PR lookup returned invalid data")
    if pr_head_oid != head_oid:
        raise ServiceError(f"pull request head does not match local HEAD: {url}")
    return url, head_oid


def _prepare_issue_branch(worktree: ResolvedProjectWorktree) -> bool:
    branch = run_git_at(
        worktree.host,
        worktree.parent,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{worktree.branch}",
    )
    if branch.returncode == 0:
        return False
    if branch.returncode != 1:
        raise ServiceError("git branch lookup failed: " + _process_detail(branch))
    origin = run_git_at(worktree.host, worktree.parent, "remote", "get-url", "origin")
    if origin.returncode != 0:
        raise ServiceError("git origin lookup failed: " + _process_detail(origin))
    try:
        configured = github_repository(worktree.repository_url)
        actual = github_repository(origin.stdout.strip())
    except ValueError as error:
        raise ServiceError(str(error)) from error
    if configured != actual:
        raise ServiceError("git.url does not match worktree parent origin")
    _require_gh(
        worktree,
        worktree.parent,
        "issue",
        "develop",
        str(worktree.issue_number),
        "--repo",
        configured,
        "--base",
        worktree.base_branch,
        "--name",
        worktree.branch,
    )
    return True


def _add_worktree(worktree: ResolvedProjectWorktree) -> None:
    arguments = ("worktree", "add", str(worktree.destination), worktree.branch)
    result = run_git_at(worktree.host, worktree.parent, *arguments)
    if result.returncode != 0:
        raise ServiceError("git worktree add failed: " + _process_detail(result))


def _rollback_open(worktree: ResolvedProjectWorktree, created_branch: bool) -> None:
    result = run_git_at(
        worktree.host, worktree.parent, "worktree", "remove", str(worktree.destination)
    )
    if result.returncode != 0:
        raise ServiceError("git worktree rollback failed: " + _process_detail(result))
    if not created_branch:
        return
    _rollback_branch(worktree)


def _rollback_branch(worktree: ResolvedProjectWorktree) -> None:
    result = run_git_at(
        worktree.host, worktree.parent, "branch", "-D", worktree.branch
    )
    if result.returncode != 0:
        raise ServiceError("git branch rollback failed: " + _process_detail(result))


def _require_clean_worktree(
    manifest: Manifest, workspace_root: Path, worktree: ResolvedProjectWorktree
) -> None:
    status = run_git_at(
        worktree.host,
        worktree.destination,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if status.returncode != 0:
        raise ServiceError("git status failed: " + _process_detail(status))
    ignored = {
        str(path)
        for path in unchanged_generated_paths(
            manifest, workspace_root, worktree.project, worktree.issue_number
        )
    }
    fields = status.stdout.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2] != " ":
            raise ServiceError("git status returned invalid porcelain output")
        paths.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            if index >= len(fields):
                raise ServiceError("git status returned invalid rename output")
            paths.append(fields[index])
            index += 1
    dirty = [path for path in paths if path not in ignored]
    if dirty:
        raise ServiceError(
            f"worktree has uncommitted changes: {worktree.workspace_path}"
        )


def _require_git(
    worktree: ResolvedProjectWorktree, *arguments: str
) -> subprocess.CompletedProcess[str]:
    try:
        result = run_git_at(worktree.host, worktree.destination, *arguments)
    except OSError as error:
        raise ServiceError(f"git invocation failed: {error}") from error
    if result.returncode != 0:
        raise ServiceError("git " + arguments[0] + " failed: " + _process_detail(result))
    return result


def _require_gh(
    worktree: ResolvedProjectWorktree, directory: Path | str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    try:
        result = run_gh(worktree.host, directory, *arguments)
    except OSError as error:
        raise ServiceError(f"gh invocation failed: {error}") from error
    if result.returncode != 0:
        raise ServiceError("gh " + arguments[0] + " failed: " + _process_detail(result))
    return result


def _process_detail(result: subprocess.CompletedProcess[str]) -> str:
    return result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
