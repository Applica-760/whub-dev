import os
import subprocess
from unittest.mock import Mock, call, patch

import pytest

from whub.core.tmux import TmuxSession
from whub.models.agent.terminal_bridge import TerminalAccessMode, TerminalSessionRef
from whub.services.agent.terminal_bridge import (
    TerminalAccessError,
    TerminalAccessRegistry,
    TerminalAttachment,
    attach,
    resize,
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


def test_attach_overrides_dumb_terminal_for_xterm_client() -> None:
    master_fd, slave_fd = os.pipe()
    process = Mock(poll=Mock(return_value=0))
    session = TmuxSession(
        name="whub-whub-dev-TASK-101",
        attach_command=("tmux", "attach-session", "-t", "=whub-whub-dev-TASK-101"),
    )

    with (
        patch.dict(os.environ, {"TERM": "dumb", "COLORTERM": ""}),
        patch("whub.services.agent.terminal_bridge.pty.openpty", return_value=(master_fd, slave_fd)),
        patch("whub.services.agent.terminal_bridge.subprocess.Popen", return_value=process) as popen,
    ):
        attachment = attach(session)

    environment = popen.call_args.kwargs["env"]
    assert environment["TERM"] == "xterm-256color"
    assert environment["COLORTERM"] == "truecolor"
    attachment.close()


def test_resize_skips_an_unchanged_terminal_size() -> None:
    attachment = TerminalAttachment(10, Mock())

    with patch("whub.services.agent.terminal_bridge.fcntl.ioctl") as ioctl:
        resize(attachment, 120, 40)
        resize(attachment, 120, 40)
        resize(attachment, 121, 40)

    assert ioctl.call_count == 2
