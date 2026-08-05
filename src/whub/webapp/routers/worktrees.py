"""Registered worktree JSON API."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.core.context import current_context
from whub.services.manifest import load_manifest
from whub.services.worktree import collect_worktree_status


router = APIRouter(prefix="/api/worktrees")


class WorktreeResponse(BaseModel):
    parent_project: str | None
    task_id: str | None
    branch: str | None
    workspace_path: str | None
    diagnostics: list[str]


class WorktreeListResponse(BaseModel):
    worktrees: list[WorktreeResponse]


@router.get("", response_model=WorktreeListResponse)
def get_worktrees() -> WorktreeListResponse:
    worktrees = collect_worktree_status(
        load_manifest(), current_context().workspace_root
    )
    return WorktreeListResponse(
        worktrees=[
            WorktreeResponse(
                parent_project=item.parent_project,
                task_id=item.task_id,
                branch=item.branch,
                workspace_path=item.workspace_path,
                diagnostics=list(item.diagnostics),
            )
            for item in worktrees
        ]
    )
