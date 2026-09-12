"""Terminal WebSocket API."""

from fastapi import APIRouter, WebSocket

from whub.models.agent.terminal_bridge import (
    TerminalSessionRef,
)
from whub.services.agent.terminal_bridge import (
    TerminalAccessRegistry,
)
from whub.services.agent.tmux_session import resolve_tmux_session
from whub.services.manifest import load_manifest
from whub.services.worktree.resolve import resolve_conventional_worktree
from whub.webapp.terminal_bridge import terminal_bridge
from whub.core.context import current_context

router = APIRouter(prefix="/api/terminals")
access = TerminalAccessRegistry()


@router.websocket("/{project}/{issue_number}")
async def terminal(websocket: WebSocket, project: str, issue_number: int) -> None:
    """Bridge one localhost WebSocket to an existing Agent tmux session."""
    session = TerminalSessionRef(project=project, issue_number=issue_number)
    worktree = resolve_conventional_worktree(
        load_manifest(), current_context().workspace_root, project, issue_number
    )
    await terminal_bridge(
        websocket,
        session,
        access,
        lambda: resolve_tmux_session(project, str(issue_number), worktree.host),
    )
