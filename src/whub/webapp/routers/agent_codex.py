"""Local API for the minimal Codex App Server client."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from whub.core.context import current_context
from whub.models import load_manifest
from whub.services.agent.app_server import app_servers
from whub.services.worktree.operation import resolve_project_worktree


router = APIRouter(prefix="/api/agent-codex")


class TurnStart(BaseModel):
    prompt: str = Field(min_length=1)


class ApprovalDecision(BaseModel):
    decision: Literal["accept", "decline"]


class AgentMessageResponse(BaseModel):
    turn_id: str
    text: str


class ApprovalResponse(BaseModel):
    request_id: int | str
    thread_id: str
    turn_id: str
    item_id: str
    command: str | None
    cwd: str | None
    reason: str | None


class AgentCodexState(BaseModel):
    thread_id: str | None
    active_turn_id: str | None
    messages: list[AgentMessageResponse]
    approvals: list[ApprovalResponse]
    error: str | None


def _session(project: str, task_id: str):
    return app_servers.get(project, task_id)


def _require_localhost(request: Request) -> None:
    if request.client is None or request.client.host != "127.0.0.1":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def _worktree(project: str, task_id: str):
    context = current_context()
    return resolve_project_worktree(
        load_manifest(), context.workspace_root, project, task_id
    ).destination


@router.post("/{project}/{task_id}/session", status_code=status.HTTP_204_NO_CONTENT)
def start_session(project: str, task_id: str, request: Request) -> Response:
    _require_localhost(request)
    app_servers.open(project, task_id, _worktree(project, task_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{project}/{task_id}/session", status_code=status.HTTP_204_NO_CONTENT)
def stop_session(project: str, task_id: str, request: Request) -> Response:
    _require_localhost(request)
    app_servers.close(project, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project}/{task_id}", response_model=AgentCodexState)
def get_state(project: str, task_id: str) -> AgentCodexState:
    return AgentCodexState.model_validate(_session(project, task_id).snapshot())


@router.post("/{project}/{task_id}/turns", status_code=status.HTTP_202_ACCEPTED)
def start_turn(project: str, task_id: str, body: TurnStart) -> None:
    _session(project, task_id).start_turn(body.prompt)


@router.post("/{project}/{task_id}/approvals/{request_id}")
def decide_approval(
    project: str, task_id: str, request_id: str, body: ApprovalDecision
) -> None:
    parsed_id: int | str = int(request_id) if request_id.isdecimal() else request_id
    _session(project, task_id).decide(parsed_id, body.decision)
