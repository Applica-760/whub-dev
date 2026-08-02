"""PR change and unified-diff JSON API for registered task worktrees."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.core.context import current_context
from whub.models import load_manifest
from whub.services.worktree.diff import (
    ChangedFile,
    WorktreeDiff,
    list_changed_files,
    read_changed_file_diff,
)

router = APIRouter(prefix="/api/worktrees/{project}/{task_id}")


class ChangedFileResponse(BaseModel):
    path: str
    status: str
    previous_path: str | None = None


class ChangedFileListResponse(BaseModel):
    files: list[ChangedFileResponse]


class WorktreeDiffResponse(BaseModel):
    path: str
    content: str


def _changed_file_response(item: ChangedFile) -> ChangedFileResponse:
    return ChangedFileResponse(
        path=item.path,
        status=item.status,
        previous_path=item.previous_path,
    )


@router.get("/changes", response_model=ChangedFileListResponse)
def get_changed_files(project: str, task_id: str) -> ChangedFileListResponse:
    return ChangedFileListResponse(
        files=[
            _changed_file_response(item)
            for item in list_changed_files(
                load_manifest(),
                current_context().workspace_root,
                project,
                task_id,
            )
        ]
    )


@router.get("/diff", response_model=WorktreeDiffResponse)
def get_worktree_diff(project: str, task_id: str, path: str) -> WorktreeDiffResponse:
    diff: WorktreeDiff = read_changed_file_diff(
        load_manifest(),
        current_context().workspace_root,
        project,
        task_id,
        path,
    )
    return WorktreeDiffResponse(path=diff.path, content=diff.content)
