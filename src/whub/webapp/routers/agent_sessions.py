"""Running Agent session JSON API."""

from fastapi import APIRouter
from pydantic import BaseModel

from whub.core.context import current_context
from whub.services.agent.agent import list_agent_sessions
from whub.services.manifest import load_manifest
from whub.services.worktree.resolve import resolve_project_worktree


router = APIRouter(prefix="/api/agent-sessions")


class AgentSessionResponse(BaseModel):
    project: str
    task_id: str
    workspace_path: str


class AgentSessionListResponse(BaseModel):
    sessions: list[AgentSessionResponse]


@router.get("/{project}", response_model=AgentSessionListResponse)
def get_agent_sessions(project: str) -> AgentSessionListResponse:
    manifest = load_manifest()
    workspace_root = current_context().workspace_root
    return AgentSessionListResponse(
        sessions=[
            AgentSessionResponse(
                project=item.project,
                task_id=item.task_id,
                workspace_path=resolve_project_worktree(
                    manifest, workspace_root, item.project, item.task_id
                ).workspace_path,
            )
            for item in list_agent_sessions(manifest, workspace_root, project)
        ]
    )
