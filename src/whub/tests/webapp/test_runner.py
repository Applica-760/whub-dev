"""Managed web app runner tests."""

from __future__ import annotations

import json
import os
import signal
import socket
import time
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, call, patch

import uvicorn
from fastapi import WebSocket
from websockets.sync.client import connect

from whub.webapp.runner import (
    AppProcessRecord,
    _stop_process_group,
    read_pid_record,
    remove_pid_record,
    serve,
    write_pid_record,
)
from whub.webapp.server import create_api_app


def test_pid_record_round_trip(tmp_path: Path) -> None:
    pid_path = tmp_path / "app.pid"

    write_pid_record(pid_path, 8710)

    assert read_pid_record(pid_path) == AppProcessRecord(
        pid=os.getpid(),
        port=8710,
        processes={"server": os.getpid()},
    )


def test_reads_legacy_pid_record_as_normal_mode(tmp_path: Path) -> None:
    pid_path = tmp_path / "app.pid"
    pid_path.write_text(json.dumps({"pid": 42, "port": 8710}) + "\n")

    assert read_pid_record(pid_path) == AppProcessRecord(pid=42, port=8710)


def test_remove_pid_record_only_removes_expected_process(tmp_path: Path) -> None:
    pid_path = tmp_path / "app.pid"
    write_pid_record(pid_path, 8710)

    remove_pid_record(pid_path, expected_pid=-1)
    assert pid_path.exists()

    remove_pid_record(pid_path, expected_pid=os.getpid())
    assert not pid_path.exists()


def test_serve_removes_its_pid_record_after_shutdown(tmp_path: Path) -> None:
    pid_path = tmp_path / "app.pid"

    def run_server(app, **kwargs) -> None:
        del app
        assert read_pid_record(pid_path) == AppProcessRecord(
            pid=os.getpid(),
            port=8710,
            processes={"server": os.getpid()},
        )
        assert kwargs == {
            "host": "127.0.0.1",
            "port": 8710,
            "log_level": "warning",
            "access_log": False,
        }

    with patch("whub.webapp.runner.uvicorn.run", side_effect=run_server):
        serve(tmp_path / "dist", 8710, pid_path)

    assert not pid_path.exists()


def test_uvicorn_accepts_terminal_websocket_upgrade() -> None:
    async def terminal_probe(
        websocket: WebSocket, project: str, issue_number: int
    ) -> None:
        await websocket.accept()
        await websocket.send_text(f"{project}/{issue_number}")
        await websocket.close()

    with patch("whub.webapp.server.terminal", terminal_probe):
        app = create_api_app()

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, log_level="error", lifespan="off", access_log=False)
    )
    thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started

        with connect(
            f"ws://127.0.0.1:{port}/api/terminals/whub-dev/99"
        ) as socket_client:
            assert socket_client.recv() == "whub-dev/99"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()

    assert not thread.is_alive()


def test_stop_process_group_terminates_all_children() -> None:
    process = Mock()
    process.pid = 42
    process.poll.return_value = None

    with (
        patch("whub.webapp.runner.os.getpgid", return_value=42),
        patch("whub.webapp.runner.os.killpg") as killpg,
    ):
        _stop_process_group(process)

    assert killpg.call_args_list == [call(42, signal.SIGTERM)]
    process.wait.assert_called_once_with(timeout=1)
