"""Lifecycle for workspace-wide Operator Terminals."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from threading import Lock
from uuid import uuid4

from whub.core.context import WhubContext
from whub.core.tmux import TmuxSession, session_name, session_target, tmux_command
from whub.models.operator_terminal import OperatorTerminal, OperatorTerminals
from whub.services.errors import ServiceError


@dataclass(frozen=True)
class _RunningOperatorTerminal:
    operator_id: str
    session: TmuxSession


class OperatorTerminalService:
    """Own the ephemeral lifecycle of workspace-wide terminals."""

    def __init__(self) -> None:
        self._lock = Lock()

    def list(self, context: WhubContext) -> OperatorTerminals:
        with self._lock:
            return OperatorTerminals(
                terminals=[
                    OperatorTerminal(operator_id=running.operator_id)
                    for running in self._load(context)
                ]
            )

    def start(self, context: WhubContext) -> OperatorTerminal:
        with self._lock:
            running = self._load(context)
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

            terminal = _RunningOperatorTerminal(
                operator_id=operator_id,
                session=TmuxSession(
                    name=name,
                    attach_command=tuple(tmux_command("attach-session", "-t", target)),
                ),
            )
            self._save(context, [*running, terminal])
            return OperatorTerminal(operator_id=operator_id)

    def resolve(self, context: WhubContext, operator_id: str) -> TmuxSession:
        with self._lock:
            for running in self._load(context):
                if running.operator_id == operator_id:
                    return running.session
            raise ServiceError("Operator terminal is not running")

    def stop(self, context: WhubContext, operator_id: str) -> OperatorTerminals:
        with self._lock:
            running = self._load(context)
            terminal = next(
                (item for item in running if item.operator_id == operator_id), None
            )
            if terminal is None:
                raise ServiceError("Operator terminal is not running")
            target = session_target(terminal.session.name)
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
            remaining = [item for item in running if item != terminal]
            self._save(context, remaining)
            return OperatorTerminals(
                terminals=[OperatorTerminal(operator_id=item.operator_id) for item in remaining]
            )

    def _load(self, context: WhubContext) -> list[_RunningOperatorTerminal]:
        path = context.operator_terminals_path
        if not path.exists():
            legacy = self._load_legacy(context)
            if legacy:
                self._save(context, legacy)
            return legacy

        running = self._read(path)
        active = [item for item in running if self._session_exists(item.session)]
        if active != running:
            self._save(context, active)
        return active

    def _load_legacy(self, context: WhubContext) -> list[_RunningOperatorTerminal]:
        path = context.operator_terminal_path
        legacy = self._read(path)
        path.unlink(missing_ok=True)
        return [item for item in legacy if self._session_exists(item.session)]

    def _read(self, path: Path) -> list[_RunningOperatorTerminal]:
        try:
            value = json.loads(path.read_text())
            records = value.get("terminals")
            if records is None:
                records = [value]
            if not isinstance(records, list):
                raise ValueError
            running = [self._record(record) for record in records]
        except (FileNotFoundError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return []
        return running

    @staticmethod
    def _record(value: object) -> _RunningOperatorTerminal:
        if not isinstance(value, dict):
            raise ValueError
        operator_id = value["operator_id"]
        name = value["tmux_session"]
        if not isinstance(operator_id, str) or not isinstance(name, str):
            raise ValueError
        target = session_target(name)
        return _RunningOperatorTerminal(
            operator_id=operator_id,
            session=TmuxSession(name, tuple(tmux_command("attach-session", "-t", target))),
        )

    @staticmethod
    def _session_exists(session: TmuxSession) -> bool:
        target = session_target(session.name)
        try:
            exists = subprocess.run(
                tmux_command("has-session", "-t", target), capture_output=True, text=True
            )
        except OSError as error:
            raise ServiceError(f"tmux is unavailable: {error}") from error
        return exists.returncode == 0

    @staticmethod
    def _save(context: WhubContext, running: list[_RunningOperatorTerminal]) -> None:
        path = context.operator_terminals_path
        if not running:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "terminals": [
                        {
                            "operator_id": item.operator_id,
                            "tmux_session": item.session.name,
                        }
                        for item in running
                    ]
                }
            )
            + "\n"
        )


operator_terminal = OperatorTerminalService()
