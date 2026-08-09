"""Create and remove resource-specific Git worktrees."""

from __future__ import annotations

from pathlib import Path

from whub.models import Manifest, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.task.project import load_project_task
from whub.services.worktree.definition import save_worktree_definition
from whub.services.worktree.git import process_detail, run_worktree_git
from whub.services.worktree.resolve import _resolve_location

def create_project_worktree(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> Path | str:
    """Create a worktree for an existing Task in PROJECT."""
    task = load_project_task(manifest, project, task_id)
    resolved_task_id = task.task.id
    number = resolved_task_id.removeprefix("TASK-")
    definition = WorktreeDefinition(
        task_id=resolved_task_id,
        parent_project=project,
        branch=f"tasks/{number}",
    )
    return _create_worktree(manifest, workspace_root, definition)


def _create_worktree(
    manifest: Manifest, workspace_root: Path, definition: WorktreeDefinition
) -> Path | str:
    """Save DEFINITION, then create its Git worktree and branch if needed."""
    parent, destination, host = _resolve_location(manifest, workspace_root, definition)
    save_worktree_definition(workspace_root, definition)
    branch_ref = f"refs/heads/{definition.branch}"
    branch_check = run_worktree_git(
        host, parent, "show-ref", "--verify", "--quiet", branch_ref
    )
    if branch_check.returncode == 0:
        command = ("worktree", "add", str(destination), definition.branch)
    elif branch_check.returncode == 1:
        command = ("worktree", "add", "-b", definition.branch, str(destination))
    else:
        raise ServiceError("git branch lookup failed: " + process_detail(branch_check))
    result = run_worktree_git(host, parent, *command)
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
    parent, destination, host = _resolve_location(manifest, workspace_root, definition)
    status = run_worktree_git(
        host, destination, "status", "--porcelain", "--untracked-files=all"
    )
    if status.returncode != 0:
        raise ServiceError("git status failed: " + process_detail(status))
    if status.stdout.strip():
        raise ServiceError(f"worktree has uncommitted changes: {destination}")
    result = run_worktree_git(host, parent, "worktree", "remove", str(destination))
    if result.returncode != 0:
        raise ServiceError("git worktree remove failed: " + process_detail(result))
    try:
        inspection.record.path.unlink()
    except OSError as error:
        raise ServiceError(
            f"failed to remove worktree definition: {inspection.record.path}: {error}"
        ) from error
