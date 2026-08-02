"""Lifecycle for the single task-independent Operator Terminal."""

from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
from threading import Lock
from uuid import uuid4

from whub.core.tmux import session_name, session_target, tmux_command
from whub.core.context import WhubContext
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

    def status(self, context: WhubContext) -> OperatorTerminal:
        with self._lock:
            return self._status(context)

    def start(self, context: WhubContext) -> OperatorTerminal:
        with self._lock:
            if self._load(context) is not None:
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
                        str(context.workspace_root),
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

            self._save(context, _RunningOperatorTerminal(
                operator_id=operator_id,
                session=TmuxSession(
                    name=name,
                    attach_command=tuple(tmux_command("attach-session", "-t", target)),
                ),
            ))
            return self._status(context)

    def resolve(self, context: WhubContext, operator_id: str) -> TmuxSession:
        with self._lock:
            running = self._load(context)
            if running is None or running.operator_id != operator_id:
                raise ServiceError("Operator terminal is not running")
            return running.session

    def stop(self, context: WhubContext) -> OperatorTerminal:
        with self._lock:
            running = self._load(context)
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
            context.operator_terminal_path.unlink(missing_ok=True)
            return self._status(context)

    def _status(self, context: WhubContext) -> OperatorTerminal:
        running = self._load(context)
        if running is None:
            return OperatorTerminal(state=OperatorTerminalState.OFF)
        return OperatorTerminal(
            state=OperatorTerminalState.ON,
            operator_id=running.operator_id,
        )

    def _load(self, context: WhubContext) -> _RunningOperatorTerminal | None:
        path = context.operator_terminal_path
        try:
            value = json.loads(path.read_text())
            operator_id = value["operator_id"]
            name = value["tmux_session"]
            if not isinstance(operator_id, str) or not isinstance(name, str):
                raise ValueError
        except (FileNotFoundError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None
        target = session_target(name)
        try:
            exists = subprocess.run(
                tmux_command("has-session", "-t", target), capture_output=True, text=True
            )
        except OSError as error:
            raise ServiceError(f"tmux is unavailable: {error}") from error
        if exists.returncode:
            path.unlink(missing_ok=True)
            return None
        return _RunningOperatorTerminal(
            operator_id=operator_id,
            session=TmuxSession(name, tuple(tmux_command("attach-session", "-t", target))),
        )

    @staticmethod
    def _save(context: WhubContext, running: _RunningOperatorTerminal) -> None:
        path = context.operator_terminal_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"operator_id": running.operator_id, "tmux_session": running.session.name}) + "\n")


operator_terminal = OperatorTerminalService()
