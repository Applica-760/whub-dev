import os
from io import StringIO
from pathlib import Path
from subprocess import CompletedProcess
from threading import Lock
from unittest.mock import Mock, patch

import pytest

from whub.services.agent.codex.app_server import (
    AppServerRegistry,
    AppServerSession,
    _codex_executable,
)
from whub.services.agent.codex.attention import approval_attention
from whub.services.errors import ServiceError


def _session(*, exit_code: int | None = None) -> AppServerSession:
    session = AppServerSession.__new__(AppServerSession)
    session.project = "whub-dev"
    session.task_id = "TASK-104"
    session.worktree = Path("/workspace/worktree")
    session.process = Mock(poll=Mock(return_value=exit_code), stdout=StringIO())
    session.stdin = StringIO()
    session.thread_id = None
    session.messages = []
    session.approvals = {}
    session.active_turn_id = None
    session.error = None
    session._closed = False
    session._next_id = 1
    session._lock = Lock()
    return session


def test_codex_executable_skips_broken_path_entries(tmp_path: Path) -> None:
    broken_dir = tmp_path / "broken"
    working_dir = tmp_path / "working"
    broken_dir.mkdir()
    working_dir.mkdir()
    broken = broken_dir / "codex"
    working = working_dir / "codex"
    broken.touch(mode=0o755)
    working.touch(mode=0o755)

    with (
        patch.dict(
            os.environ,
            {"PATH": f"{broken_dir}{os.pathsep}{working_dir}"},
            clear=False,
        ),
        patch(
            "whub.services.agent.codex.app_server.subprocess.run",
            side_effect=[
                CompletedProcess([str(broken), "--version"], 1),
                CompletedProcess([str(working), "--version"], 0),
            ],
        ) as run,
    ):
        assert _codex_executable() == str(working)

    assert [call.args[0][0] for call in run.call_args_list] == [
        str(broken),
        str(working),
    ]


def test_app_server_json_rpc_error_is_reported_and_blocks_turns() -> None:
    session = _session()

    session._handle({"id": 1, "error": {"message": "unsupported method"}})

    assert session.snapshot()["error"] == (
        "Codex App Server JSON-RPC error: unsupported method"
    )
    with pytest.raises(ServiceError, match="unsupported method"):
        session.start_turn("continue")


def test_app_server_invalid_json_is_reported() -> None:
    session = _session()
    session.process.stdout = StringIO("not json\n")

    session._read()

    assert session.snapshot()["error"] == "Codex App Server returned invalid JSON"


def test_app_server_process_exit_is_reported() -> None:
    session = _session(exit_code=1)

    assert session.snapshot()["error"] == "Codex App Server stopped (exit code 1)"


def test_closing_app_server_clears_task_attention() -> None:
    registry = AppServerRegistry()
    session = Mock()
    registry._sessions[("whub-dev", "TASK-104")] = session
    approval_attention.request("whub-dev", "TASK-104", "command", "turn-1")

    registry.close("whub-dev", "TASK-104")

    session.close.assert_called_once_with()
    assert approval_attention.list() == ()
