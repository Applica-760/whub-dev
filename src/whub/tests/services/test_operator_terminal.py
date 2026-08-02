"""Operator Terminal lifecycle tests."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from whub.models.operator_terminal import OperatorTerminalState
from whub.services.errors import ServiceError
from whub.services.operator_terminal import OperatorTerminalService


def test_start_creates_one_login_shell_in_workspace_root(tmp_path: Path) -> None:
    service = OperatorTerminalService()
    context = SimpleNamespace(
        workspace_root=Path("/workspace-hub"),
        operator_terminal_path=tmp_path / "operator-terminal.json",
    )
    result = Mock(returncode=0, stderr="")
    generated_id = Mock(hex="operator-1")

    with (
        patch("whub.services.operator_terminal.uuid4", return_value=generated_id),
        patch("whub.services.operator_terminal.subprocess.run", side_effect=[result, result, result]) as run,
    ):
        status = service.start(context)
        assert service.resolve(context, "operator-1").name == "whub-operator-operator-1"

    assert status.state is OperatorTerminalState.ON
    assert status.operator_id == "operator-1"
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


def test_stop_removes_the_record_and_rejects_the_previous_id(tmp_path: Path) -> None:
    service = OperatorTerminalService()
    context = SimpleNamespace(
        workspace_root=Path("/workspace-hub"),
        operator_terminal_path=tmp_path / "operator-terminal.json",
    )
    created = Mock(returncode=0, stderr="")
    stopped = Mock(returncode=0, stderr="")

    with patch(
        "whub.services.operator_terminal.subprocess.run",
        side_effect=[created, created, created, stopped],
    ) as run:
        with patch(
            "whub.services.operator_terminal.uuid4", return_value=Mock(hex="operator-1")
        ):
            service.start(context)
        status = service.stop(context)

    assert status.state is OperatorTerminalState.OFF
    assert status.operator_id is None
    assert run.call_args.args[0] == [
        "tmux",
        "kill-session",
        "-t",
        "=whub-operator-operator-1",
    ]
    with pytest.raises(ServiceError, match="not running"):
        service.resolve(context, "operator-1")


def test_start_rejects_a_second_active_operator(tmp_path: Path) -> None:
    service = OperatorTerminalService()
    context = SimpleNamespace(
        workspace_root=Path("/workspace-hub"),
        operator_terminal_path=tmp_path / "operator-terminal.json",
    )
    created = Mock(returncode=0, stderr="")

    with (
        patch("whub.services.operator_terminal.subprocess.run", return_value=created),
        patch("whub.services.operator_terminal.uuid4", return_value=Mock(hex="operator-1")),
    ):
        service.start(context)
        with pytest.raises(ServiceError, match="already running"):
            service.start(context)
