"""Safe creation and removal of registered Git worktrees."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from whub.models import Manifest, RemoteResource, SymlinkResource, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.task import load_project_task
from whub.services.worktree.definition import save_worktree_definition
from whub.services.worktree.github import run_gh
from whub.services.worktree.git import process_detail, run_git


@dataclass(frozen=True)
class ResolvedProjectWorktree:
    """One consistent registered worktree and its PR lifecycle inputs."""

    definition: WorktreeDefinition
    parent: Path
    destination: Path
    base_branch: str
_MERGE_METHODS = frozenset(("merge", "squash", "rebase"))


def _require_worktree_parent(manifest: Manifest, project: str) -> SymlinkResource:
    """Resolve a Project eligible to own a local Git worktree."""
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    resource = resolved_project.resource
    if resource is None:
        raise ServiceError(f"project has no resource: {project}")
    if isinstance(resource, RemoteResource):
        raise ServiceError(
            f"worktree for remote resource is not implemented: {project}"
        )
    if not isinstance(resource, SymlinkResource):
        raise ServiceError(f"not a local resource: {project}")
    if resource.git is None:
        raise ServiceError(f"worktree parent has no git declaration: {project}")
    return resource


def resolve_worktree_parent(manifest: Manifest, definition: WorktreeDefinition) -> Path:
    """Resolve DEFINITION's current local parent repository path."""
    return Path(_require_worktree_parent(manifest, definition.parent_project).source)


def resolve_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> ResolvedProjectWorktree:
    """Resolve one cleanly registered worktree and its GitHub PR inputs."""
    from whub.services.worktree.check import inspect_worktrees

    inspection = next(
        (
            item
            for item in inspect_worktrees(manifest, workspace_root)
            if item.definition is not None
            and item.definition.parent_project == project
            and item.definition.task_id == task_id
        ),
        None,
    )
    if inspection is None:
        raise ServiceError(f"worktree definition not found: {project}/{task_id}")
    if inspection.diagnostics:
        raise ServiceError(
            "cannot use inconsistent worktree: " + "; ".join(inspection.diagnostics)
        )
    definition = inspection.definition
    assert definition is not None
    resource = _require_worktree_parent(manifest, project)
    assert resource.git is not None
    if resource.git.branch is None:
        raise ServiceError(f"worktree parent has no git branch declaration: {project}")
    load_project_task(manifest, project, definition.task_id)
    return ResolvedProjectWorktree(
        definition=definition,
        parent=Path(resource.source),
        destination=workspace_root / definition.workspace_path,
        base_branch=resource.git.branch,
    )


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
            raise ServiceError(
                f"open pull request not found: {project}/{task_id}"
            )
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


def create_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> Path:
    """Create a worktree for an existing Task in PROJECT."""
    task = load_project_task(manifest, project, task_id)
    resolved_task_id = task.task.id
    number = resolved_task_id.removeprefix("TASK-")
    definition = WorktreeDefinition(
        task_id=resolved_task_id,
        parent_project=project,
        branch=f"tasks/{number}",
        workspace_path=f"projects/worktrees/{project}-{number}",
    )
    return _create_worktree(manifest, workspace_root, definition)


def _create_worktree(
    manifest: Manifest,
    workspace_root: Path,
    definition: WorktreeDefinition,
) -> Path:
    """Save DEFINITION, then create its Git worktree and branch if needed."""
    parent = resolve_worktree_parent(manifest, definition)
    destination = workspace_root / definition.workspace_path
    save_worktree_definition(workspace_root, definition)
    branch_ref = f"refs/heads/{definition.branch}"
    branch_check = run_git(parent, "show-ref", "--verify", "--quiet", branch_ref)
    if branch_check.returncode == 0:
        command = ("worktree", "add", str(destination), definition.branch)
    elif branch_check.returncode == 1:
        command = ("worktree", "add", "-b", definition.branch, str(destination))
    else:
        raise ServiceError("git branch lookup failed: " + process_detail(branch_check))
    result = run_git(parent, *command)
    if result.returncode != 0:
        raise ServiceError("git worktree add failed: " + process_detail(result))
    return destination


def remove_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> None:
    """Remove PROJECT's clean, consistent worktree for TASK_ID."""
    from whub.services.worktree.check import inspect_worktrees

    inspection = next(
        (
            item
            for item in inspect_worktrees(manifest, workspace_root)
            if item.definition is not None
            and item.definition.parent_project == project
            and item.definition.task_id == task_id
        ),
        None,
    )
    if inspection is None:
        raise ServiceError(f"worktree definition not found: {project}/{task_id}")
    if inspection.diagnostics:
        raise ServiceError(
            "cannot remove inconsistent worktree: " + "; ".join(inspection.diagnostics)
        )
    definition = inspection.definition
    assert definition is not None
    parent = resolve_worktree_parent(manifest, definition)
    destination = workspace_root / definition.workspace_path
    status = run_git(destination, "status", "--porcelain", "--untracked-files=all")
    if status.returncode != 0:
        raise ServiceError("git status failed: " + process_detail(status))
    if status.stdout.strip():
        raise ServiceError(
            f"worktree has uncommitted changes: {definition.workspace_path}"
        )
    result = run_git(parent, "worktree", "remove", str(destination))
    if result.returncode != 0:
        raise ServiceError("git worktree remove failed: " + process_detail(result))
    try:
        inspection.record.path.unlink()
    except OSError as error:
        raise ServiceError(
            f"failed to remove worktree definition: {inspection.record.path}: {error}"
        ) from error
