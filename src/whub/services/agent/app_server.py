"""Own one Codex App Server process for each registered Agent worktree."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, Thread
from typing import Any, TextIO

from whub.services.errors import ServiceError
from whub.services.agent.attention import approval_attention


@dataclass(frozen=True)
class ApprovalRequest:
    request_id: int | str
    thread_id: str
    turn_id: str
    item_id: str
    command: str | None
    cwd: str | None
    reason: str | None


@dataclass(frozen=True)
class AgentMessage:
    turn_id: str
    text: str


def _codex_executable() -> str:
    """Return the first runnable Codex executable from the current PATH."""
    candidates: list[str] = []
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / "codex"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            value = str(candidate)
            if value not in candidates:
                candidates.append(value)
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "--version"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
        except OSError:
            continue
        if result.returncode == 0:
            return candidate
    raise ServiceError("no runnable Codex CLI was found on PATH")


@dataclass
class AppServerSession:
    """A JSONL App Server client with a deliberately small local state model."""

    project: str
    task_id: str
    worktree: Path
    process: subprocess.Popen[str]
    stdin: TextIO
    thread_id: str | None = None
    messages: list[AgentMessage] = field(default_factory=list)
    approvals: dict[int | str, ApprovalRequest] = field(default_factory=dict)
    active_turn_id: str | None = None
    error: str | None = None
    _closed: bool = False
    _next_id: int = 1
    _lock: Lock = field(default_factory=Lock, repr=False)

    def __post_init__(self) -> None:
        Thread(target=self._read, daemon=True).start()
        self._send(
            "initialize",
            {
                "clientInfo": {
                    "name": "whub",
                    "title": "Workspace Hub",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self._notify("initialized", {})
        self._send("thread/start", {"cwd": str(self.worktree)})

    def start_turn(self, prompt: str) -> None:
        if not prompt.strip():
            raise ServiceError("prompt is required")
        self._require_available()
        with self._lock:
            thread_id = self.thread_id
        if thread_id is None:
            raise ServiceError("Codex App Server thread is not ready")
        self._send(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt.strip()}],
                "cwd": str(self.worktree),
            },
        )

    def decide(self, request_id: int | str, decision: str) -> None:
        self._require_available()
        with self._lock:
            if request_id not in self.approvals:
                raise ServiceError("approval request is unavailable")
        self._write({"id": request_id, "result": {"decision": decision}})

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            self._refresh_process_state()
            return {
                "thread_id": self.thread_id,
                "active_turn_id": self.active_turn_id,
                "messages": [message.__dict__ for message in self.messages],
                "approvals": [request.__dict__ for request in self.approvals.values()],
                "error": self.error,
            }

    def close(self) -> None:
        with self._lock:
            self._closed = True
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def _send(self, method: str, params: dict[str, object]) -> int:
        request_id = self._next_id
        self._next_id += 1
        self._write({"method": method, "id": request_id, "params": params})
        return request_id

    def _notify(self, method: str, params: dict[str, object]) -> None:
        self._write({"method": method, "params": params})

    def _write(self, message: dict[str, object]) -> None:
        with self._lock:
            self._refresh_process_state()
            if self.error is not None:
                raise ServiceError(self.error)
            try:
                self.stdin.write(json.dumps(message) + "\n")
                self.stdin.flush()
            except OSError as error:
                self._set_error(f"failed to write to Codex App Server: {error}")
                raise ServiceError(self.error) from error

    def _read(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    with self._lock:
                        self._set_error("Codex App Server returned invalid JSON")
                    return
                if not isinstance(message, dict):
                    with self._lock:
                        self._set_error(
                            "Codex App Server returned an invalid JSON-RPC message"
                        )
                    return
                self._handle(message)
        except OSError as error:
            with self._lock:
                self._set_error(f"failed to read from Codex App Server: {error}")
        finally:
            with self._lock:
                self._refresh_process_state()

    def _handle(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        with self._lock:
            if "error" in message:
                error = message["error"]
                detail = error.get("message") if isinstance(error, dict) else None
                self._set_error(
                    f"Codex App Server JSON-RPC error: {detail}"
                    if isinstance(detail, str) and detail
                    else "Codex App Server returned a JSON-RPC error"
                )
                return
            if method is not None and not isinstance(method, str):
                self._set_error("Codex App Server returned an invalid JSON-RPC method")
                return
            params = message.get("params", {})
            if not isinstance(params, dict):
                self._set_error("Codex App Server returned invalid JSON-RPC parameters")
                return
            if "result" in message and isinstance(message["result"], dict):
                thread = message["result"].get("thread")
                if isinstance(thread, dict) and isinstance(thread.get("id"), str):
                    self.thread_id = thread["id"]
            if method == "turn/started":
                turn = params.get("turn")
                if isinstance(turn, dict) and isinstance(turn.get("id"), str):
                    self.active_turn_id = turn["id"]
                else:
                    self._set_error("Codex App Server returned an invalid turn event")
            elif method == "turn/completed":
                self.active_turn_id = None
            elif method == "item/agentMessage/delta":
                delta = params.get("delta")
                turn_id = params.get("turnId")
                if isinstance(delta, str) and isinstance(turn_id, str):
                    self.messages.append(AgentMessage(turn_id, delta))
            elif method == "item/commandExecution/requestApproval":
                request_id = message.get("id")
                if request_id is not None:
                    thread_id = params.get("threadId")
                    turn_id = params.get("turnId")
                    item_id = params.get("itemId")
                    if not all(
                        isinstance(value, str) and value
                        for value in (thread_id, turn_id, item_id)
                    ):
                        self._set_error(
                            "Codex App Server approval request is missing identifiers"
                        )
                        return
                    self.approvals[request_id] = ApprovalRequest(
                        request_id=request_id,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=item_id,
                        command=params.get("command"),
                        cwd=params.get("cwd"),
                        reason=params.get("reason"),
                    )
                    approval_attention.request(
                        self.project,
                        self.task_id,
                        params.get("command")
                        or params.get("reason")
                        or "Codex command",
                        turn_id,
                    )
            elif method == "serverRequest/resolved":
                request = self.approvals.pop(params.get("requestId"), None)
                if request is not None:
                    approval_attention.clear(
                        self.project,
                        self.task_id,
                        request.command or request.reason or "Codex command",
                        request.turn_id,
                    )

    def _require_available(self) -> None:
        with self._lock:
            self._refresh_process_state()
            if self.error is not None:
                raise ServiceError(self.error)

    def _refresh_process_state(self) -> None:
        exit_code = self.process.poll()
        if exit_code is not None and not self._closed:
            self._set_error(f"Codex App Server stopped (exit code {exit_code})")

    def _set_error(self, detail: str) -> None:
        if self.error is None:
            self.error = detail


class AppServerRegistry:
    """Process ownership boundary shared by the Agent harness and web API."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str], AppServerSession] = {}
        self._lock = Lock()

    def open(self, project: str, task_id: str, worktree: Path) -> AppServerSession:
        key = (project, task_id)
        with self._lock:
            existing = self._sessions.get(key)
            if existing is not None and existing.process.poll() is None:
                return existing
            if existing is not None:
                existing.close()
                approval_attention.clear_task(project, task_id)
            try:
                process = subprocess.Popen(
                    [_codex_executable(), "app-server"],
                    cwd=worktree,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                )
            except OSError as error:
                raise ServiceError(
                    f"failed to start Codex App Server: {error}"
                ) from error
            if process.stdin is None:
                process.kill()
                raise ServiceError("Codex App Server stdin is unavailable")
            try:
                session = AppServerSession(
                    project, task_id, worktree, process, process.stdin
                )
            except ServiceError:
                process.kill()
                process.wait()
                raise
            self._sessions[key] = session
            return session

    def get(self, project: str, task_id: str) -> AppServerSession:
        with self._lock:
            session = self._sessions.get((project, task_id))
        if session is None:
            raise ServiceError("Codex App Server is not running")
        return session

    def close(self, project: str, task_id: str) -> None:
        with self._lock:
            session = self._sessions.pop((project, task_id), None)
        if session is not None:
            session.close()
        approval_attention.clear_task(project, task_id)


app_servers = AppServerRegistry()
