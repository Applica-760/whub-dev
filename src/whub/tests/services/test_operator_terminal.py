"""Operator Terminal lifecycle tests."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from whub.services.errors import ServiceError
from whub.services.operator_terminal import OperatorTerminalService


def _context(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        workspace_root=Path("/workspace-hub"),
        operator_terminal_path=tmp_path / "operator-terminal.json",
        operator_terminals_path=tmp_path / "operator-terminals.json",
    )


def test_start_creates_multiple_login_shells_in_workspace_root(tmp_path: Path) -> None:
    service = OperatorTerminalService()
    context = _context(tmp_path)
    result = Mock(returncode=0, stderr="")

    with (
        patch(
            "whub.services.operator_terminal.uuid4",
            side_effect=[Mock(hex="operator-1"), Mock(hex="operator-2")],
        ),
        patch("whub.services.operator_terminal.subprocess.run", return_value=result) as run,
    ):
        first = service.start(context)
        second = service.start(context)
        listed = service.list(context)

    assert [item.operator_id for item in listed.terminals] == ["operator-1", "operator-2"]
    assert [first.operator_id, second.operator_id] == ["operator-1", "operator-2"]
    assert run.call_args_list[0].args[0] == [
        "tmux",
        "new-session",
        "-d",
        "-s",
        "whub-operator-operator-1",
        "-c",
        "/workspace-hub",
        "exec $SHELL -l",
    ]
    assert run.call_args_list[2].args[0] == [
        "tmux",
        "new-session",
        "-d",
        "-s",
        "whub-operator-operator-2",
        "-c",
        "/workspace-hub",
        "exec $SHELL -l",
    ]


def test_stop_removes_only_the_selected_record_and_rejects_its_id(tmp_path: Path) -> None:
    service = OperatorTerminalService()
    context = _context(tmp_path)
    context.operator_terminals_path.write_text(
        json.dumps(
            {
                "terminals": [
                    {"operator_id": "operator-1", "tmux_session": "whub-operator-operator-1"},
                    {"operator_id": "operator-2", "tmux_session": "whub-operator-operator-2"},
                ]
            }
        )
    )
    result = Mock(returncode=0, stderr="")

    with patch("whub.services.operator_terminal.subprocess.run", return_value=result) as run:
        remaining = service.stop(context, "operator-1")
        assert service.resolve(context, "operator-2").name == "whub-operator-operator-2"

    assert [item.operator_id for item in remaining.terminals] == ["operator-2"]
    assert run.call_args_list[2].args[0] == [
        "tmux",
        "kill-session",
        "-t",
        "=whub-operator-operator-1",
    ]
    with pytest.raises(ServiceError, match="not running"):
        service.resolve(context, "operator-1")


def test_load_migrates_the_active_legacy_record(tmp_path: Path) -> None:
    service = OperatorTerminalService()
    context = _context(tmp_path)
    context.operator_terminal_path.write_text(
        json.dumps(
            {"operator_id": "operator-1", "tmux_session": "whub-operator-operator-1"}
        )
    )
    result = Mock(returncode=0, stderr="")

    with patch("whub.services.operator_terminal.subprocess.run", return_value=result):
        listed = service.list(context)

    assert [item.operator_id for item in listed.terminals] == ["operator-1"]
    assert not context.operator_terminal_path.exists()
    assert json.loads(context.operator_terminals_path.read_text()) == {
        "terminals": [
            {"operator_id": "operator-1", "tmux_session": "whub-operator-operator-1"}
        ]
    }
