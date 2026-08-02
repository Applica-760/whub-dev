"""Terminal WebSocket bridge tests."""

from __future__ import annotations

import asyncio
import os
import socket
import threading
from unittest.mock import Mock, patch

import anyio
import pytest

from whub.models.agent.terminal_bridge import TerminalAccessMode, TerminalSessionRef
from whub.services.agent.terminal_bridge import TerminalAttachment
from whub.webapp.routers.terminal import access, terminal


class FakeWebSocket:
    def __init__(self) -> None:
        self.headers = {"host": "localhost"}
        self.messages: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self.output: asyncio.Queue[str] = asyncio.Queue()
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def receive(self) -> dict[str, object]:
        return await self.messages.get()

    async def send_text(self, data: str) -> None:
        await self.output.put(data)

    async def send_json(self, data: object) -> None:
        await self.output.put(str(data))

    async def close(self, code: int) -> None:
        del code


async def _receive(peer: socket.socket) -> bytes:
    await anyio.wait_readable(peer)
    return peer.recv(4096)


def test_input_echo_and_disconnect_share_one_long_lived_output_pump() -> None:
    async def exercise() -> None:
        websocket = FakeWebSocket()
        server, peer = socket.socketpair()
        attachment = TerminalAttachment(server.detach(), Mock(poll=Mock(return_value=0)))
        session = TerminalSessionRef(project="whub-dev", task_id="TASK-100")

        with (
            patch("whub.webapp.routers.terminal.resolve_tmux_session"),
            patch("whub.webapp.terminal_bridge.attach", return_value=attachment),
        ):
            bridge = asyncio.create_task(terminal(websocket, session.project, session.task_id))
            await websocket.messages.put({"type": "websocket.receive", "text": '{"type":"claim"}'})
            await websocket.messages.put(
                {"type": "websocket.receive", "text": '{"type":"input","data":"l"}'}
            )
            assert await _receive(peer) == b"l"

            peer.sendall(b"l")
            async with asyncio.timeout(1):
                assert await websocket.output.get() == "l"

            await websocket.messages.put(
                {"type": "websocket.receive", "text": '{"type":"input","data":"1"}'}
            )
            assert await _receive(peer) == b"1"

            await websocket.messages.put({"type": "websocket.disconnect"})
            async with asyncio.timeout(1):
                await bridge

        assert websocket.accepted
        assert access.access_mode(session, str(id(websocket))) is TerminalAccessMode.VIEWER
        with pytest.raises(OSError):
            os.fstat(attachment.master_fd)
        peer.close()

    asyncio.run(exercise())


def test_disconnect_releases_control_for_immediate_reconnect() -> None:
    async def exercise() -> None:
        first_websocket = FakeWebSocket()
        second_websocket = FakeWebSocket()
        first_server, first_peer = socket.socketpair()
        second_server, second_peer = socket.socketpair()
        attachments = [
            TerminalAttachment(first_server.detach(), Mock(poll=Mock(return_value=0))),
            TerminalAttachment(second_server.detach(), Mock(poll=Mock(return_value=0))),
        ]
        session = TerminalSessionRef(project="whub-dev", task_id="TASK-100")

        with (
            patch("whub.webapp.routers.terminal.resolve_tmux_session"),
            patch("whub.webapp.terminal_bridge.attach", side_effect=attachments),
        ):
            first_bridge = asyncio.create_task(
                terminal(first_websocket, session.project, session.task_id)
            )
            await first_websocket.messages.put(
                {"type": "websocket.receive", "text": '{"type":"claim"}'}
            )
            await first_websocket.messages.put({"type": "websocket.disconnect"})
            async with asyncio.timeout(1):
                await first_bridge

            second_bridge = asyncio.create_task(
                terminal(second_websocket, session.project, session.task_id)
            )
            await second_websocket.messages.put(
                {"type": "websocket.receive", "text": '{"type":"claim"}'}
            )
            await second_websocket.messages.put(
                {"type": "websocket.receive", "text": '{"type":"input","data":"2"}'}
            )
            assert await _receive(second_peer) == b"2"
            await second_websocket.messages.put({"type": "websocket.disconnect"})
            async with asyncio.timeout(1):
                await second_bridge

        first_peer.close()
        second_peer.close()

    asyncio.run(exercise())


def test_attachment_cleanup_does_not_block_the_event_loop() -> None:
    async def exercise() -> None:
        websocket = FakeWebSocket()
        server, peer = socket.socketpair()
        attachment = TerminalAttachment(server.detach(), Mock(poll=Mock(return_value=0)))
        cleanup_started = threading.Event()
        allow_cleanup = threading.Event()

        def slow_close() -> None:
            cleanup_started.set()
            allow_cleanup.wait(timeout=1)

        attachment.close = Mock(side_effect=slow_close)

        with (
            patch("whub.webapp.routers.terminal.resolve_tmux_session"),
            patch("whub.webapp.terminal_bridge.attach", return_value=attachment),
        ):
            bridge = asyncio.create_task(terminal(websocket, "whub-dev", "TASK-100"))
            await websocket.messages.put({"type": "websocket.disconnect"})
            while not cleanup_started.is_set():
                await asyncio.sleep(0)
            assert not bridge.done()
            allow_cleanup.set()
            async with asyncio.timeout(1):
                await bridge

        attachment.close.assert_called_once_with()
        os.close(attachment.master_fd)
        peer.close()

    asyncio.run(exercise())
