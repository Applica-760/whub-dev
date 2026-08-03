"""Operator Terminal HTTP and WebSocket API."""

from __future__ import annotations

from fastapi import APIRouter, Response, WebSocket, status

from whub.core.context import current_context
from whub.models.operator_terminal import OperatorTerminal, OperatorTerminalRef, OperatorTerminals
from whub.services.agent.terminal_bridge import TerminalAccessRegistry
from whub.services.operator_terminal import operator_terminal
from whub.webapp.terminal_bridge import terminal_bridge


router = APIRouter(prefix="/api/operator-terminals")
access = TerminalAccessRegistry()


@router.get("", response_model=OperatorTerminals)
def list_operator_terminals() -> OperatorTerminals:
    return operator_terminal.list(current_context())


@router.post("", response_model=OperatorTerminal, status_code=status.HTTP_201_CREATED)
def start_operator_terminal() -> OperatorTerminal:
    return operator_terminal.start(current_context())


@router.delete("/{operator_id}", status_code=status.HTTP_204_NO_CONTENT)
def stop_operator_terminal(operator_id: str) -> Response:
    operator_terminal.stop(current_context(), operator_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def operator_terminal_socket(websocket: WebSocket, operator_id: str) -> None:
    """Bridge a running Operator Terminal and reject stale identifiers."""
    terminal = OperatorTerminalRef(operator_id=operator_id)
    await terminal_bridge(
        websocket,
        terminal,
        access,
        lambda: operator_terminal.resolve(current_context(), terminal.operator_id),
    )
