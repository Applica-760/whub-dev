import pytest

from whub.models.agent.terminal_bridge import TerminalAccessMode, TerminalSessionRef
from whub.services.agent.terminal_bridge import TerminalAccessError, TerminalAccessRegistry


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
