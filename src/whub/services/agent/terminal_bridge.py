"""Runtime access control and PTY attachment for Agent terminal bridges."""

import os
import pty
import subprocess
import fcntl
import struct
import termios
from dataclasses import dataclass, field

from whub.services.agent.tmux_session import TmuxSession

from whub.models.agent.terminal_bridge import (
    TerminalAccessMode,
    TerminalLease,
    TerminalSessionRef,
)
from whub.models.operator_terminal import OperatorTerminalRef


TerminalConnectionRef = TerminalSessionRef | OperatorTerminalRef


class TerminalAccessError(Exception):
    """Raised when a connection cannot control a terminal session."""


class TerminalAccessRegistry:
    """Keep non-persistent controller leases for terminal sessions."""

    def __init__(self) -> None:
        self._controllers: dict[tuple[str, str], str] = {}

    @staticmethod
    def _key(session: TerminalConnectionRef) -> tuple[str, str]:
        if isinstance(session, OperatorTerminalRef):
            return "operator", session.operator_id
        return session.project, session.task_id

    def access_mode(
        self, session: TerminalConnectionRef, connection_id: str
    ) -> TerminalAccessMode:
        if self._controllers.get(self._key(session)) == connection_id:
            return TerminalAccessMode.CONTROLLER
        return TerminalAccessMode.VIEWER

    def claim(self, session: TerminalConnectionRef, connection_id: str) -> TerminalLease:
        key = self._key(session)
        controller = self._controllers.get(key)
        if controller is not None and controller != connection_id:
            raise TerminalAccessError("terminal controller is already assigned")
        self._controllers[key] = connection_id
        return TerminalLease(
            session=session,
            connection_id=connection_id,
            mode=TerminalAccessMode.CONTROLLER,
        )

    def release(self, session: TerminalConnectionRef, connection_id: str) -> None:
        key = self._key(session)
        if self._controllers.get(key) == connection_id:
            del self._controllers[key]

    def disconnect(self, connection_id: str) -> None:
        for session, controller in tuple(self._controllers.items()):
            if controller == connection_id:
                del self._controllers[session]

    def require_controller(self, session: TerminalConnectionRef, connection_id: str) -> None:
        if self.access_mode(session, connection_id) is not TerminalAccessMode.CONTROLLER:
            raise TerminalAccessError("terminal controller is required")


@dataclass
class TerminalAttachment:
    master_fd: int
    process: subprocess.Popen[bytes]
    _closed: bool = field(default=False, init=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.master_fd >= 0:
            master_fd = self.master_fd
            self.master_fd = -1
            os.close(master_fd)
        if self.process.poll() is None:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def attach(session: TmuxSession) -> TerminalAttachment:
    """Attach a PTY client to an existing tmux session."""
    master, slave = pty.openpty()
    environment = os.environ.copy()
    environment.update(TERM="xterm-256color", COLORTERM="truecolor")
    try:
        process = subprocess.Popen(
            session.attach_command,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env=environment,
        )
    finally:
        os.close(slave)
    return TerminalAttachment(master, process)


def resize(attachment: TerminalAttachment, columns: int, rows: int) -> None:
    fcntl.ioctl(attachment.master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
