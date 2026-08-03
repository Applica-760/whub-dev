"""Local-only API for Codex approval attention."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.services.agent.attention import approval_attention


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
