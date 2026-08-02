"""Lifecycle for the single task-independent Operator Terminal."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from threading import Lock
from uuid import uuid4

from whub.core.tmux import session_name, session_target, tmux_command
from whub.models.operator_terminal import (
    OperatorTerminal,
    OperatorTerminalState,
)
from whub.services.agent.tmux_session import TmuxSession
from whub.services.errors import ServiceError


@dataclass(frozen=True)
class _RunningOperatorTerminal:
    operator_id: str
    session: TmuxSession


class OperatorTerminalService:
    """Own the ephemeral lifecycle of one workspace-wide terminal."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._running: _RunningOperatorTerminal | None = None

    def status(self) -> OperatorTerminal:
        with self._lock:
            return self._status()

    def start(self, workspace_root: Path) -> OperatorTerminal:
        with self._lock:
            if self._running is not None:
                raise ServiceError("Operator terminal is already running")

            operator_id = uuid4().hex
            name = session_name("operator", operator_id)
            target = session_target(name)
            command = "exec $SHELL -l"
            try:
                created = subprocess.run(
                    tmux_command(
                        "new-session",
                        "-d",
                        "-s",
                        name,
                        "-c",
                        str(workspace_root),
                        command,
                    ),
                    capture_output=True,
                    text=True,
                )
            except OSError as error:
                raise ServiceError(f"failed to start Operator terminal: {error}") from error
            if created.returncode != 0:
                detail = created.stderr.strip() or f"exit status {created.returncode}"
                raise ServiceError(f"failed to start Operator terminal: {detail}")

            self._running = _RunningOperatorTerminal(
                operator_id=operator_id,
                session=TmuxSession(
                    name=name,
                    attach_command=tuple(tmux_command("attach-session", "-t", target)),
                ),
            )
            return self._status()

    def resolve(self, operator_id: str) -> TmuxSession:
        with self._lock:
            if self._running is None or self._running.operator_id != operator_id:
                raise ServiceError("Operator terminal is not running")
            return self._running.session

    def stop(self) -> OperatorTerminal:
        with self._lock:
            running = self._running
            if running is None:
                raise ServiceError("Operator terminal is not running")
            target = session_target(running.session.name)
            try:
                stopped = subprocess.run(
                    tmux_command("kill-session", "-t", target),
                    capture_output=True,
                    text=True,
                )
            except OSError as error:
                raise ServiceError(f"failed to stop Operator terminal: {error}") from error
            if stopped.returncode != 0:
                detail = stopped.stderr.strip() or f"exit status {stopped.returncode}"
                raise ServiceError(f"failed to stop Operator terminal: {detail}")
            self._running = None
            return self._status()

    def _status(self) -> OperatorTerminal:
        if self._running is None:
            return OperatorTerminal(state=OperatorTerminalState.OFF)
        return OperatorTerminal(
            state=OperatorTerminalState.ON,
            operator_id=self._running.operator_id,
        )


operator_terminal = OperatorTerminalService()
