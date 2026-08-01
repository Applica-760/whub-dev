import os
import subprocess
from unittest.mock import Mock, call

import pytest

from whub.models.agent.terminal_bridge import TerminalAccessMode, TerminalSessionRef
from whub.services.agent.terminal_bridge import (
    TerminalAccessError,
    TerminalAccessRegistry,
    TerminalAttachment,
)


def test_controller_is_explicit_and_unique() -> None:
    registry = TerminalAccessRegistry()
    session = TerminalSessionRef(project="whub-dev", task_id="TASK-094")

    assert registry.access_mode(session, "a") is TerminalAccessMode.VIEWER
    registry.claim(session, "a")
    assert registry.access_mode(session, "a") is TerminalAccessMode.CONTROLLER

    with pytest.raises(TerminalAccessError, match="already assigned"):
        registry.claim(session, "b")


def test_disconnect_releases_controller() -> None:
    registry = TerminalAccessRegistry()
    session = TerminalSessionRef(project="whub-dev", task_id="TASK-094")
    registry.claim(session, "a")

    registry.disconnect("a")

    assert registry.access_mode(session, "a") is TerminalAccessMode.VIEWER
    assert registry.claim(session, "b").connection_id == "b"


def test_viewer_cannot_send_terminal_input() -> None:
    registry = TerminalAccessRegistry()
    session = TerminalSessionRef(project="whub-dev", task_id="TASK-094")

    with pytest.raises(TerminalAccessError, match="controller is required"):
        registry.require_controller(session, "viewer")


def test_attachment_close_reaps_process_and_is_idempotent() -> None:
    master_fd, peer_fd = os.pipe()
    process = Mock()
    process.poll.return_value = None
    attachment = TerminalAttachment(master_fd, process)

    attachment.close()
    attachment.close()

    assert attachment.master_fd == -1
    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=1)
    os.close(peer_fd)


def test_attachment_close_kills_process_that_ignores_terminate() -> None:
    master_fd, peer_fd = os.pipe()
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired("tmux", 1), 0]
    attachment = TerminalAttachment(master_fd, process)

    attachment.close()

    process.kill.assert_called_once_with()
    assert process.wait.call_args_list == [call(timeout=1), call()]
    os.close(peer_fd)
