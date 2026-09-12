"""Local-only API for Codex terminal attention."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field, model_validator

from whub.core.context import current_context
from whub.models import SymlinkResource
from whub.services.agent.codex.attention import ApprovalAttention, approval_attention
from whub.services.agent.tmux_session import resolve_tmux_session
from whub.services.errors import ServiceError
from whub.services.manifest import load_manifest
from whub.services.operator_terminal import operator_terminal
from whub.services.worktree.resolve import (
    LOCAL_WORKTREE_ROOT,
    resolve_conventional_worktree,
)
from whub.webapp.runner import HOST


router = APIRouter(prefix="/api/agent-attention")
attention = approval_attention
_subscribers: set[WebSocket] = set()


class ApprovalAttentionResponse(BaseModel):
    target: Literal["worktree", "operator"]
    event: Literal["permission_request", "response_completed"]
    requested_at: str
    acknowledged: bool
    project: str | None = None
    issue_number: int | None = None
    operator_id: str | None = None
    tool_name: str | None = None


class ApprovalAttentionListResponse(BaseModel):
    attention: list[ApprovalAttentionResponse]


class HookEvent(BaseModel):
    hook_event_name: Literal["PermissionRequest", "PostToolUse", "Stop"]
    session_id: str = Field(min_length=1)
    cwd: str = Field(min_length=1)
    turn_id: str = Field(min_length=1)
    tool_name: str | None = None
    operator_id: str | None = None

    @model_validator(mode="after")
    def require_tool_for_tool_events(self) -> HookEvent:
        if self.hook_event_name != "Stop" and not self.tool_name:
            raise ValueError("tool_name is required for tool Hook events")
        return self


def _response(item: ApprovalAttention) -> ApprovalAttentionResponse:
    project, issue_number = (
        item.target_id.split("/", 1) if item.target == "worktree" else (None, None)
    )
    return ApprovalAttentionResponse(
        target=item.target,
        event=item.event,
        requested_at=item.requested_at.isoformat(),
        acknowledged=item.acknowledged,
        project=project,
        issue_number=int(issue_number) if issue_number is not None else None,
        operator_id=item.target_id if item.target == "operator" else None,
        tool_name=item.tool_name,
    )


def _require_localhost(request: Request) -> None:
    if request.client is None or request.client.host != HOST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


async def _publish(event: str | None = None) -> None:
    message = {"type": "attention_updated"}
    if event is not None:
        message["event"] = event
    disconnected: list[WebSocket] = []
    for subscriber in tuple(_subscribers):
        try:
            await subscriber.send_json(message)
        except (RuntimeError, WebSocketDisconnect):
            disconnected.append(subscriber)
    for subscriber in disconnected:
        _subscribers.discard(subscriber)


@router.websocket("/stream")
async def attention_stream(websocket: WebSocket) -> None:
    """Push attention changes without sharing terminal WebSocket connections."""
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host", "")
    if origin is not None and origin not in {f"http://{host}", f"https://{host}"}:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    _subscribers.add(websocket)
    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers.discard(websocket)


def _registered_worktree(cwd: str) -> tuple[str, int]:
    context = current_context()
    manifest = load_manifest()
    path = Path(cwd)
    if path.parent != context.workspace_root / LOCAL_WORKTREE_ROOT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for project in manifest.projects:
        prefix = f"{project.name}-"
        number = path.name.removeprefix(prefix)
        if not path.name.startswith(prefix) or not number.isdecimal():
            continue
        resolved = manifest.resolve_project(project.name)
        if resolved is None or not isinstance(resolved.resource, SymlinkResource):
            continue
        try:
            worktree = resolve_conventional_worktree(
                manifest,
                context.workspace_root,
                project.name,
                int(number),
            )
            resolve_tmux_session(worktree.project, str(worktree.issue_number), worktree.host)
        except ServiceError:
            continue
        if cwd == str(worktree.destination):
            return worktree.project, worktree.issue_number
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _registered_target(body: HookEvent) -> tuple[str, str, str | None, int | None]:
    if body.operator_id is not None:
        try:
            operator_terminal.resolve(current_context(), body.operator_id)
        except ServiceError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
        return "operator", body.operator_id, None, None
    project, issue_number = _registered_worktree(body.cwd)
    return "worktree", f"{project}/{issue_number}", project, issue_number


@router.get("", response_model=ApprovalAttentionListResponse)
def get_attention() -> ApprovalAttentionListResponse:
    return ApprovalAttentionListResponse(
        attention=[_response(item) for item in attention.list()]
    )


@router.post(
    "/operator/{operator_id}/acknowledge",
    response_model=list[ApprovalAttentionResponse],
)
async def acknowledge_operator_attention(
    operator_id: str,
) -> list[ApprovalAttentionResponse]:
    updated = [_response(item) for item in attention.acknowledge_operator(operator_id)]
    await _publish()
    return updated


@router.post(
    "/{project}/{issue_number}/acknowledge", response_model=list[ApprovalAttentionResponse]
)
async def acknowledge_worktree_attention(
    project: str, issue_number: int
) -> list[ApprovalAttentionResponse]:
    updated = [
        _response(item) for item in attention.acknowledge(project, str(issue_number))
    ]
    await _publish()
    return updated


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
async def record_hook_event(body: HookEvent, request: Request) -> Response:
    _require_localhost(request)
    target, target_id, project, issue_number = _registered_target(body)
    event: str | None = None
    if body.hook_event_name == "PermissionRequest":
        if target == "operator":
            attention.request_operator(
                target_id,
                body.tool_name or "",
                body.turn_id,
                session_id=body.session_id,
            )
        else:
            attention.request(
                project or "",
                str(issue_number or ""),
                body.tool_name or "",
                body.turn_id,
                session_id=body.session_id,
            )
        event = "permission_request"
    elif body.hook_event_name == "PostToolUse":
        if target == "operator":
            attention.clear_operator_permission(
                target_id, body.tool_name, body.turn_id, session_id=body.session_id
            )
        else:
            attention.clear(
                project or "",
                str(issue_number or ""),
                body.tool_name or "",
                body.turn_id,
                session_id=body.session_id,
            )
    elif target == "operator":
        attention.complete_operator(target_id, body.turn_id, session_id=body.session_id)
        event = "response_completed"
    else:
        attention.complete(
            project or "", str(issue_number or ""), body.turn_id, session_id=body.session_id
        )
        event = "response_completed"
    await _publish(event)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
