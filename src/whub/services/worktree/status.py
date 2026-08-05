"""Read-only worktree state for status and web adapters."""

from __future__ import annotations

from pathlib import Path

from whub.models import Manifest, WorktreeInspection, WorktreeStatus
from whub.services.errors import ServiceError
from whub.services.worktree.check import inspect_worktrees
from whub.services.worktree.resolve import _resolve_location


def collect_worktree_status(
    manifest: Manifest, workspace_root: Path
) -> list[WorktreeStatus]:
    """Return every registered worktree and its consistency diagnostics."""
    return [
        _status_from_inspection(manifest, workspace_root, item)
        for item in inspect_worktrees(manifest, workspace_root)
    ]


def _status_from_inspection(
    manifest: Manifest, workspace_root: Path, inspection: WorktreeInspection
) -> WorktreeStatus:
    definition = inspection.definition
    if definition is None:
        return WorktreeStatus(None, None, None, None, inspection.diagnostics)
    try:
        _, destination, _ = _resolve_location(manifest, workspace_root, definition)
    except ServiceError:
        destination = None
    return WorktreeStatus(
        parent_project=definition.parent_project,
        task_id=definition.task_id,
        branch=definition.branch,
        workspace_path=str(destination) if destination is not None else None,
        diagnostics=inspection.diagnostics,
    )
