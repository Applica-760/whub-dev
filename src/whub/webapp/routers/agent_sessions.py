"""Running Agent session JSON API."""

from fastapi import APIRouter
from pydantic import BaseModel

from whub.core.context import current_context
from whub.models import RemoteResource
from whub.services.agent.agent import list_agent_sessions
from whub.services.errors import ServiceError
from whub.services.manifest import load_manifest


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
    resolved = manifest.resolve_project(project)
    if resolved is not None and (
        resolved.resource is None
        or resolved.resource.git is None
        or resolved.resource.git.branch is None
    ):
        return AgentSessionListResponse(sessions=[])
    if resolved is not None and isinstance(resolved.resource, RemoteResource):
        try:
            sessions = list_agent_sessions(manifest, workspace_root, project)
        except ServiceError:
            return AgentSessionListResponse(sessions=[])
    else:
        sessions = list_agent_sessions(manifest, workspace_root, project)
    return AgentSessionListResponse(
        sessions=[
            AgentSessionResponse(
                project=item.project,
                task_id=item.task_id,
                workspace_path=item.workspace_path,
            )
            for item in sessions
        ]
    )
