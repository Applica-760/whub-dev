from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from whub.core.context import WhubContext
from whub.services.errors import ServiceError
from whub.webapp import agent_codex_control
from whub.webapp.runner import AppProcessRecord


def _context(tmp_path: Path) -> WhubContext:
    return WhubContext(tmp_path)


def test_start_requests_the_running_dev_app(tmp_path: Path) -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    with (
        patch(
            "whub.webapp.agent_codex_control.read_pid_record",
            side_effect=[AppProcessRecord(100, 8712), None],
        ),
        patch(
            "whub.webapp.agent_codex_control.urlopen", return_value=response
        ) as request,
    ):
        agent_codex_control.start(_context(tmp_path), "whub-dev", "TASK-104")

    assert request.call_args.args[0].method == "POST"
    assert request.call_args.args[0].full_url.endswith(
        "/api/agent-codex/whub-dev/TASK-104/session"
    )


def test_control_requires_a_running_web_app(tmp_path: Path) -> None:
    with patch(
        "whub.webapp.agent_codex_control.read_pid_record", return_value=None
    ):
        with pytest.raises(ServiceError, match="web app is not running"):
            agent_codex_control.stop(_context(tmp_path), "whub-dev", "TASK-104")
