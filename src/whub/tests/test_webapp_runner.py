"""Managed web app runner tests."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from whub.webapp.runner import (
    AppProcessRecord,
    read_pid_record,
    remove_pid_record,
    serve,
    write_pid_record,
)


def test_pid_record_round_trip(tmp_path: Path) -> None:
    pid_path = tmp_path / "app.pid"

    write_pid_record(pid_path, 8710)

    assert read_pid_record(pid_path) == AppProcessRecord(pid=os.getpid(), port=8710)


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
        assert read_pid_record(pid_path) == AppProcessRecord(pid=os.getpid(), port=8710)
        assert kwargs == {
            "host": "127.0.0.1",
            "port": 8710,
            "log_level": "warning",
            "access_log": False,
        }

    with patch("whub.webapp.runner.uvicorn.run", side_effect=run_server):
        serve(tmp_path / "dist", 8710, pid_path)

    assert not pid_path.exists()
