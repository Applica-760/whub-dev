"""Terminal WebSocket API."""

from fastapi import APIRouter, WebSocket

from whub.models.agent.terminal_bridge import (
    TerminalSessionRef,
)
from whub.services.agent.terminal_bridge import (
    TerminalAccessRegistry,
)
from whub.services.agent.tmux_session import resolve_tmux_session
from whub.webapp.terminal_bridge import terminal_bridge

router = APIRouter(prefix="/api/terminals")
access = TerminalAccessRegistry()


@router.websocket("/{project}/{task_id}")
async def terminal(websocket: WebSocket, project: str, task_id: str) -> None:
    """Bridge one localhost WebSocket to an existing Agent tmux session."""
    session = TerminalSessionRef(project=project, task_id=task_id)
    await terminal_bridge(
        websocket, session, access, lambda: resolve_tmux_session(project, task_id)
    )
