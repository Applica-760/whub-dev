"""Task worktree open and close operations."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess

from whub.core.remote import run_ssh_command
from whub.core.tmux import TmuxSession
from whub.models import Manifest
from whub.services.agent.agent import (
    close_agent,
    open_agent,
    unchanged_generated_paths,
)
from whub.services.errors import ServiceError
from whub.services.worktree.git import process_detail, run_worktree_git
from whub.services.worktree.resolve import (
    ResolvedProjectWorktree,
    resolve_project_worktree,
    resolve_task_worktree,
    resolve_worktree,
)


def open_project_worktree(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
    auth_names: tuple[str, ...],
) -> TmuxSession:
    """Create one conventional worktree, then prepare and open its Agent."""
    worktree = resolve_worktree(manifest, workspace_root, project, task_id)
    if _destination_exists(worktree):
        return open_agent(
            manifest, workspace_root, project, worktree.task_id, auth_names
        )
    worktree = resolve_task_worktree(manifest, workspace_root, project, task_id)
    created_branch = _add_worktree(worktree)
    try:
        return open_agent(
            manifest, workspace_root, project, worktree.task_id, auth_names
        )
    except (OSError, ServiceError) as error:
        try:
            _rollback_open(worktree, created_branch)
        except ServiceError as rollback_error:
            raise ServiceError(
                f"Agent open failed: {error}; rollback failed: {rollback_error}"
            ) from error
        raise


def close_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> str:
    """Clean Agent files, merge one task PR, then remove its worktree."""
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    _require_clean_worktree(manifest, workspace_root, worktree)
    close_agent(manifest, workspace_root, project, worktree.task_id)
    url, head_oid = _push_and_create_pull_request(worktree)
    _run_gh(worktree, "pr", "merge", url, "--merge", "--match-head-commit", head_oid)
    state = _run_gh(worktree, "pr", "view", url, "--json", "state", "--jq", ".state")
    if state.stdout.strip() != "MERGED":
        raise ServiceError(f"pull request was not merged: {url}")
    try:
        _run_git(worktree, "worktree", "remove", str(worktree.destination))
    except (OSError, ServiceError) as error:
        raise ServiceError(
            f"pull request merged but cleanup failed: {error}"
        ) from error
    return url


def create_project_pull_request(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> str:
    """Push one clean task branch and create or return its pull request."""
    worktree = resolve_project_worktree(manifest, workspace_root, project, task_id)
    _require_clean_worktree(manifest, workspace_root, worktree)
    url, _ = _push_and_create_pull_request(worktree)
    return url


def _push_and_create_pull_request(worktree: ResolvedProjectWorktree) -> tuple[str, str]:
    _run_git(worktree, "push", "--set-upstream", "origin", worktree.branch)
    head_oid = _run_git(worktree, "rev-parse", "HEAD").stdout.strip()
    if not head_oid:
        raise ServiceError("git rev-parse returned no HEAD")
    url, pr_head_oid = _find_or_create_pull_request(worktree)
    if pr_head_oid != head_oid:
        raise ServiceError(f"pull request head does not match local HEAD: {url}")
    return url, head_oid


def _destination_exists(worktree: ResolvedProjectWorktree) -> bool:
    if worktree.host is None:
        assert isinstance(worktree.destination, Path)
        return worktree.destination.exists()
    assert isinstance(worktree.destination, str)
    return (
        run_ssh_command(
            worktree.host, f"test -e {shlex.quote(worktree.destination)}"
        ).returncode
        == 0
    )


def _add_worktree(worktree: ResolvedProjectWorktree) -> bool:
    branch_ref = f"refs/heads/{worktree.branch}"
    branch = run_worktree_git(
        worktree.host, worktree.parent, "show-ref", "--verify", "--quiet", branch_ref
    )
    if branch.returncode == 0:
        arguments = ("worktree", "add", str(worktree.destination), worktree.branch)
        created_branch = False
    elif branch.returncode == 1:
        arguments = (
            "worktree",
            "add",
            "-b",
            worktree.branch,
            str(worktree.destination),
        )
        created_branch = True
    else:
        raise ServiceError("git branch lookup failed: " + process_detail(branch))
    result = run_worktree_git(worktree.host, worktree.parent, *arguments)
    if result.returncode != 0:
        raise ServiceError("git worktree add failed: " + process_detail(result))
    return created_branch


def _rollback_open(worktree: ResolvedProjectWorktree, created_branch: bool) -> None:
    result = run_worktree_git(
        worktree.host, worktree.parent, "worktree", "remove", str(worktree.destination)
    )
    if result.returncode != 0:
        raise ServiceError("git worktree rollback failed: " + process_detail(result))
    if not created_branch:
        return
    result = run_worktree_git(
        worktree.host, worktree.parent, "branch", "-D", worktree.branch
    )
    if result.returncode != 0:
        raise ServiceError("git branch rollback failed: " + process_detail(result))


def _require_clean_worktree(
    manifest: Manifest, workspace_root: Path, worktree: ResolvedProjectWorktree
) -> None:
    status = run_worktree_git(
        worktree.host,
        worktree.destination,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if status.returncode != 0:
        raise ServiceError("git status failed: " + process_detail(status))
    ignored = {
        str(path)
        for path in unchanged_generated_paths(
            manifest, workspace_root, worktree.project, worktree.task_id
        )
    }
    dirty = [path for path in _status_paths(status.stdout) if path not in ignored]
    if dirty:
        raise ServiceError(
            f"worktree has uncommitted changes: {worktree.workspace_path}"
        )


def _status_paths(output: str) -> list[str]:
    fields = output.split("\0")
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
    return paths


def _run_git(
    worktree: ResolvedProjectWorktree, *arguments: str
) -> subprocess.CompletedProcess[str]:
    result = run_worktree_git(worktree.host, worktree.destination, *arguments)
    if result.returncode != 0:
        raise ServiceError("git " + arguments[0] + " failed: " + process_detail(result))
    return result


def _run_gh(
    worktree: ResolvedProjectWorktree, *arguments: str
) -> subprocess.CompletedProcess[str]:
    try:
        if worktree.host is None:
            assert isinstance(worktree.destination, Path)
            result = subprocess.run(
                ["gh", *arguments],
                cwd=worktree.destination,
                capture_output=True,
                text=True,
            )
        else:
            assert isinstance(worktree.destination, str)
            result = run_ssh_command(
                worktree.host,
                f"cd {shlex.quote(worktree.destination)} && gh {shlex.join(arguments)}",
            )
    except OSError as error:
        raise ServiceError(f"gh invocation failed: {error}") from error
    if result.returncode != 0:
        raise ServiceError("gh " + arguments[0] + " failed: " + process_detail(result))
    return result


def _find_or_create_pull_request(worktree: ResolvedProjectWorktree) -> tuple[str, str]:
    listed = _run_gh(
        worktree,
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
            f"multiple open pull requests found: {worktree.project}/{worktree.task_id}"
        )
    if pull_requests:
        return _pull_request(pull_requests[0])
    created = _run_gh(
        worktree,
        "pr",
        "create",
        "--base",
        worktree.base_branch,
        "--head",
        worktree.branch,
        "--title",
        worktree.task_id,
        "--body",
        "",
    )
    url = created.stdout.strip()
    if not url:
        raise ServiceError("gh PR create returned no URL")
    viewed = _run_gh(worktree, "pr", "view", url, "--json", "url,headRefOid")
    try:
        return _pull_request(json.loads(viewed.stdout))
    except json.JSONDecodeError as error:
        raise ServiceError("gh PR view returned invalid data") from error


def _pull_request(value: object) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise ServiceError("gh PR lookup returned invalid data")
    url = value.get("url")
    head_oid = value.get("headRefOid")
    if not isinstance(url, str) or not isinstance(head_oid, str):
        raise ServiceError("gh PR lookup returned invalid data")
    return url, head_oid
