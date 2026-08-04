"""Local-only API for Codex approval attention."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from whub.core.context import current_context
from whub.services.manifest import load_manifest
from whub.services.agent.codex.attention import approval_attention
from whub.services.worktree import inspect_worktrees


router = APIRouter(prefix="/api/agent-attention")
attention = approval_attention


class ApprovalAttentionResponse(BaseModel):
    project: str
    task_id: str
    tool_name: str
    requested_at: str
    acknowledged: bool


class ApprovalAttentionListResponse(BaseModel):
    attention: list[ApprovalAttentionResponse]


class HookEvent(BaseModel):
    hook_event_name: Literal["PermissionRequest", "PostToolUse"]
    session_id: str = Field(min_length=1)
    cwd: str = Field(min_length=1)
    turn_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)


def _require_localhost(request: Request) -> None:
    if request.client is None or request.client.host != "127.0.0.1":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _registered_task(cwd: str) -> tuple[str, str]:
    context = current_context()
    for inspection in inspect_worktrees(load_manifest(), context.workspace_root):
        definition = inspection.definition
        if (
            definition is not None
            and not inspection.diagnostics
            and cwd == str(context.workspace_root / definition.workspace_path)
        ):
            return definition.parent_project, definition.task_id
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("", response_model=ApprovalAttentionListResponse)
def get_attention() -> ApprovalAttentionListResponse:
    return ApprovalAttentionListResponse(
        attention=[
            ApprovalAttentionResponse(
                project=item.project,
                task_id=item.task_id,
                tool_name=item.tool_name,
                requested_at=item.requested_at.isoformat(),
                acknowledged=item.acknowledged,
            )
            for item in attention.list()
        ]
    )


@router.post(
    "/{project}/{task_id}/acknowledge", response_model=ApprovalAttentionResponse | None
)
def acknowledge_attention(
    project: str, task_id: str
) -> ApprovalAttentionResponse | None:
    item = attention.acknowledge(project, task_id)
    if item is None:
        return None
    return ApprovalAttentionResponse(
        project=item.project,
        task_id=item.task_id,
        tool_name=item.tool_name,
        requested_at=item.requested_at.isoformat(),
        acknowledged=item.acknowledged,
    )


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
def record_hook_event(body: HookEvent, request: Request) -> Response:
    _require_localhost(request)
    project, task_id = _registered_task(body.cwd)
    if body.hook_event_name == "PermissionRequest":
        attention.request(
            project,
            task_id,
            body.tool_name,
            body.turn_id,
            session_id=body.session_id,
        )
    else:
        attention.clear(
            project,
            task_id,
            body.tool_name,
            body.turn_id,
            session_id=body.session_id,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
