"""Terminal WebSocket API."""

import asyncio
import json
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from whub.models.agent.terminal_bridge import TerminalSessionRef
from whub.services.agent.terminal_bridge import (
    TerminalAccessError,
    TerminalAccessRegistry,
    attach,
    resize,
)
from whub.services.agent.tmux_session import resolve_tmux_session

router = APIRouter(prefix="/api/terminals")
access = TerminalAccessRegistry()


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
    try:
        while True:
            incoming = asyncio.create_task(websocket.receive())
            output = asyncio.create_task(asyncio.to_thread(os.read, attachment.master_fd, 4096))
            done, pending = await asyncio.wait({incoming, output}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            if output in done:
                await websocket.send_text(output.result().decode(errors="replace"))
            if incoming in done:
                message = incoming.result()
                if message.get("text") is not None:
                    text = message["text"]
                    try:
                        control = json.loads(text)
                    except json.JSONDecodeError:
                        access.require_controller(session, connection_id)
                        os.write(attachment.master_fd, text.encode())
                    else:
                        if control == {"type": "claim"}:
                            access.claim(session, connection_id)
                        elif control == {"type": "release"}:
                            access.release(session, connection_id)
                        elif control.get("type") == "resize":
                            access.require_controller(session, connection_id)
                            resize(attachment, int(control["columns"]), int(control["rows"]))
                        else:
                            await websocket.send_json({"type": "error", "detail": "unknown control"})
                elif message.get("type") == "websocket.receive" and message.get("bytes") is None:
                    pass
    except (TerminalAccessError, WebSocketDisconnect):
        pass
    finally:
        access.disconnect(connection_id)
        attachment.close()
