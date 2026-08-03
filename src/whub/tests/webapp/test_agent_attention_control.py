import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from whub.core.context import WhubContext
from whub.services.errors import ServiceError
from whub.webapp import agent_attention_control
from whub.webapp.runner import AppProcessRecord


def _context(tmp_path: Path) -> WhubContext:
    return WhubContext(tmp_path)


def test_submit_posts_only_the_hook_identity_fields(tmp_path: Path) -> None:
    response = MagicMock()
    response.__enter__.return_value = response
    event = {
        "hook_event_name": "PermissionRequest",
        "session_id": "session-1",
        "cwd": "/workspace/worktree",
        "turn_id": "turn-1",
        "tool_name": "Bash",
        "tool_input": {"command": "secret"},
    }
    with (
        patch(
            "whub.webapp.agent_attention_control.read_pid_record",
            side_effect=[AppProcessRecord(100, 8712), None],
        ),
        patch(
            "whub.webapp.agent_attention_control.urlopen", return_value=response
        ) as request,
    ):
        agent_attention_control.submit(_context(tmp_path), event)

    submitted = request.call_args.args[0]
    assert submitted.full_url.endswith("/api/agent-attention/events")
    assert json.loads(submitted.data) == {
        key: event[key]
        for key in ("hook_event_name", "session_id", "cwd", "turn_id", "tool_name")
    }


def test_submit_rejects_invalid_hook_events_without_contacting_the_backend(
    tmp_path: Path,
) -> None:
    with pytest.raises(ServiceError, match="invalid Codex Hook event"):
        agent_attention_control.submit(_context(tmp_path), {"hook_event_name": "Stop"})
