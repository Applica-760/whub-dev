"""Operator Terminal WebSocket tests."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from whub.services.errors import ServiceError
from whub.webapp.routers.operator_terminal import operator_terminal_socket


class RejectedWebSocket:
    headers = {"host": "localhost"}

    def __init__(self) -> None:
        self.close_codes: list[int] = []

    async def close(self, code: int = 1000) -> None:
        self.close_codes.append(code)


def test_socket_rejects_an_operator_id_after_it_has_stopped() -> None:
    async def exercise() -> None:
        websocket = RejectedWebSocket()
        with patch(
            "whub.webapp.routers.operator_terminal.operator_terminal.resolve",
            side_effect=ServiceError("Operator terminal is not running"),
        ):
            await operator_terminal_socket(websocket, "previous-id")
        assert websocket.close_codes == [1008]

    asyncio.run(exercise())
