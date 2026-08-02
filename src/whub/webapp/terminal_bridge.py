"""Shared WebSocket adapter for task and Operator tmux terminals."""

import asyncio
import json
import os
from collections.abc import Callable

import anyio
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from whub.models.agent.terminal_bridge import (
    TerminalClaim,
    TerminalInput,
    TerminalRelease,
    TerminalResize,
)
from whub.services.agent.terminal_bridge import (
    TerminalAccessError,
    TerminalAccessRegistry,
    TerminalConnectionRef,
    attach,
    resize,
)
from whub.services.agent.tmux_session import TmuxSession
from whub.services.errors import ServiceError


async def terminal_bridge(
    websocket: WebSocket,
    terminal: TerminalConnectionRef,
    access: TerminalAccessRegistry,
    resolve: Callable[[], TmuxSession],
) -> None:
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host", "")
    if origin is not None and origin not in {f"http://{host}", f"https://{host}"}:
        await websocket.close(code=1008)
        return
    try:
        attachment = attach(resolve())
    except ServiceError:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    connection_id = str(id(websocket))

    async def receive() -> None:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                return
            try:
                control = json.loads(message.get("text") or "")
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
                        raise ValueError
            except (TerminalAccessError, ValidationError, ValueError, json.JSONDecodeError):
                await websocket.send_json({"type": "error", "detail": "invalid frame"})

    async def forward() -> None:
        while True:
            await anyio.wait_readable(attachment.master_fd)
            data = os.read(attachment.master_fd, 4096)
            if not data:
                return
            await websocket.send_text(data.decode(errors="replace"))

    pumps = {asyncio.create_task(receive()), asyncio.create_task(forward())}
    try:
        done, _ = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        for pump in done:
            pump.result()
    except (OSError, WebSocketDisconnect):
        pass
    finally:
        for pump in pumps:
            pump.cancel()
        await asyncio.gather(*pumps, return_exceptions=True)
        access.disconnect(connection_id)
        await anyio.to_thread.run_sync(attachment.close)
