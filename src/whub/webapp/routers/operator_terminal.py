"""Operator Terminal HTTP and WebSocket API."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, status

from whub.core.context import current_context
from whub.models.operator_terminal import OperatorTerminal, OperatorTerminalRef
from whub.services.agent.terminal_bridge import TerminalAccessRegistry
from whub.services.operator_terminal import operator_terminal
from whub.webapp.terminal_bridge import terminal_bridge


router = APIRouter(prefix="/api/operator-terminal")
access = TerminalAccessRegistry()


@router.get("", response_model=OperatorTerminal)
def get_operator_terminal() -> OperatorTerminal:
    return operator_terminal.status(current_context())


@router.post("", response_model=OperatorTerminal, status_code=status.HTTP_201_CREATED)
def start_operator_terminal() -> OperatorTerminal:
    return operator_terminal.start(current_context())


@router.delete("", response_model=OperatorTerminal)
def stop_operator_terminal() -> OperatorTerminal:
    return operator_terminal.stop(current_context())


async def operator_terminal_socket(websocket: WebSocket, operator_id: str) -> None:
    """Bridge a running Operator Terminal and reject stale identifiers."""
    terminal = OperatorTerminalRef(operator_id=operator_id)
    await terminal_bridge(
        websocket,
        terminal,
        access,
        lambda: operator_terminal.resolve(current_context(), terminal.operator_id),
    )
