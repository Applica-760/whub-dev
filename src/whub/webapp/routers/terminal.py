"""Terminal WebSocket API."""

import asyncio
import json
import os

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from whub.models.agent.terminal_bridge import (
    TerminalClaim,
    TerminalInput,
    TerminalRelease,
    TerminalResize,
    TerminalSessionRef,
)
from whub.services.agent.terminal_bridge import (
    TerminalAttachment,
    TerminalAccessError,
    TerminalAccessRegistry,
    attach,
    resize,
)
from whub.services.agent.tmux_session import resolve_tmux_session

router = APIRouter(prefix="/api/terminals")
access = TerminalAccessRegistry()


async def _forward_output(websocket: WebSocket, master_fd: int) -> None:
    while True:
        await anyio.wait_readable(master_fd)
        data = os.read(master_fd, 4096)
        if not data:
            return
        await websocket.send_text(data.decode(errors="replace"))


async def _receive_input(
    websocket: WebSocket,
    session: TerminalSessionRef,
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
                    access.claim(session, connection_id)
                case "release":
                    TerminalRelease.model_validate(control)
                    access.release(session, connection_id)
                case "input":
                    frame = TerminalInput.model_validate(control)
                    access.require_controller(session, connection_id)
                    os.write(attachment.master_fd, frame.data.encode())
                case "resize":
                    frame = TerminalResize.model_validate(control)
                    access.require_controller(session, connection_id)
                    resize(attachment, frame.columns, frame.rows)
                case _:
                    raise ValueError("unknown frame")
        except (ValidationError, ValueError):
            await websocket.send_json({"type": "error", "detail": "invalid frame"})


@router.websocket("/{project}/{task_id}")
async def terminal(websocket: WebSocket, project: str, task_id: str) -> None:
    """Bridge one localhost WebSocket to an existing Agent tmux session."""
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host", "")
    if origin is not None and origin not in {f"http://{host}", f"https://{host}"}:
        await websocket.close(code=1008)
        return
    session = TerminalSessionRef(project=project, task_id=task_id)
    connection_id = str(id(websocket))
    attachment = attach(resolve_tmux_session(session.project, session.task_id))
    await websocket.accept()
    incoming = asyncio.create_task(
        _receive_input(
            websocket,
            session,
            connection_id,
            attachment,
        )
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
