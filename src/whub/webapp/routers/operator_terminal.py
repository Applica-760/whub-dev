"""Operator Terminal HTTP and WebSocket API."""

from __future__ import annotations

import asyncio
import json
import os

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from whub.core.context import current_context
from whub.models.agent.terminal_bridge import (
    TerminalClaim,
    TerminalInput,
    TerminalRelease,
    TerminalResize,
)
from whub.models.operator_terminal import OperatorTerminal, OperatorTerminalRef
from whub.services.agent.terminal_bridge import (
    TerminalAccessError,
    TerminalAccessRegistry,
    TerminalAttachment,
    attach,
    resize,
)
from whub.services.errors import ServiceError
from whub.services.operator_terminal import operator_terminal


router = APIRouter(prefix="/api/operator-terminal")
access = TerminalAccessRegistry()


@router.get("", response_model=OperatorTerminal)
def get_operator_terminal() -> OperatorTerminal:
    return operator_terminal.status()


@router.post("", response_model=OperatorTerminal, status_code=status.HTTP_201_CREATED)
def start_operator_terminal() -> OperatorTerminal:
    return operator_terminal.start(current_context().workspace_root)


@router.delete("", response_model=OperatorTerminal)
def stop_operator_terminal() -> OperatorTerminal:
    return operator_terminal.stop()


async def _forward_output(websocket: WebSocket, master_fd: int) -> None:
    while True:
        await anyio.wait_readable(master_fd)
        data = os.read(master_fd, 4096)
        if not data:
            return
        await websocket.send_text(data.decode(errors="replace"))


async def _receive_input(
    websocket: WebSocket,
    terminal: OperatorTerminalRef,
    connection_id: str,
    attachment: TerminalAttachment,
) -> None:
    while True:
        message = await websocket.receive()
        if message.get("type") == "websocket.disconnect":
            return
        text = message.get("text")
        if text is None:
            continue
        try:
            control = json.loads(text)
        except json.JSONDecodeError:
            control = None
        if not isinstance(control, dict):
            await websocket.send_json({"type": "error", "detail": "invalid frame"})
            continue
        try:
            match control.get("type"):
                case "claim":
                    TerminalClaim.model_validate(control)
                    access.claim(terminal, connection_id)
                case "release":
                    TerminalRelease.model_validate(control)
                    access.release(terminal, connection_id)
                case "input":
                    frame = TerminalInput.model_validate(control)
                    access.require_controller(terminal, connection_id)
                    os.write(attachment.master_fd, frame.data.encode())
                case "resize":
                    frame = TerminalResize.model_validate(control)
                    access.require_controller(terminal, connection_id)
                    resize(attachment, frame.columns, frame.rows)
                case _:
                    raise ValueError("unknown frame")
        except (TerminalAccessError, ValidationError, ValueError):
            await websocket.send_json({"type": "error", "detail": "invalid frame"})


async def operator_terminal_socket(websocket: WebSocket, operator_id: str) -> None:
    """Bridge a running Operator Terminal and reject stale identifiers."""
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host", "")
    if origin is not None and origin not in {f"http://{host}", f"https://{host}"}:
        await websocket.close(code=1008)
        return
    terminal = OperatorTerminalRef(operator_id=operator_id)
    try:
        attachment = attach(operator_terminal.resolve(terminal.operator_id))
    except ServiceError:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    connection_id = str(id(websocket))
    incoming = asyncio.create_task(
        _receive_input(websocket, terminal, connection_id, attachment)
    )
    output = asyncio.create_task(_forward_output(websocket, attachment.master_fd))
    pumps = {incoming, output}
    try:
        done, _ = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        for pump in done:
            pump.result()
    except (OSError, TerminalAccessError, WebSocketDisconnect):
        pass
    finally:
        for pump in pumps:
            pump.cancel()
        await asyncio.gather(*pumps, return_exceptions=True)
        access.disconnect(connection_id)
        await anyio.to_thread.run_sync(attachment.close)
        await websocket.close()
