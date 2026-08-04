"""Keep short-lived Codex attention events for the local web app."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Literal


ATTENTION_TTL = timedelta(minutes=10)
AttentionTarget = Literal["worktree", "operator"]
AttentionEvent = Literal["permission_request", "response_completed"]


@dataclass(frozen=True)
class ApprovalAttention:
    """One unresolved event for one immutable terminal target."""

    target: AttentionTarget
    target_id: str
    event: AttentionEvent
    requested_at: datetime
    turn_id: str
    acknowledged: bool = False
    tool_name: str | None = None
    session_id: str = ""


class ApprovalAttentionStore:
    """In-memory control-plane state for independent terminal events."""

    def __init__(self) -> None:
        self._items: dict[
            tuple[AttentionTarget, str, AttentionEvent], ApprovalAttention
        ] = {}
        self._lock = Lock()

    def request(
        self,
        project: str,
        task_id: str,
        tool_name: str,
        turn_id: str,
        now: datetime | None = None,
        session_id: str = "",
    ) -> ApprovalAttention:
        return self._record(
            "worktree",
            _worktree_target_id(project, task_id),
            "permission_request",
            turn_id,
            tool_name,
            now,
            session_id,
        )

    def request_operator(
        self,
        operator_id: str,
        tool_name: str,
        turn_id: str,
        now: datetime | None = None,
        session_id: str = "",
    ) -> ApprovalAttention:
        return self._record(
            "operator",
            operator_id,
            "permission_request",
            turn_id,
            tool_name,
            now,
            session_id,
        )

    def complete(
        self,
        project: str,
        task_id: str,
        turn_id: str,
        now: datetime | None = None,
        session_id: str = "",
    ) -> ApprovalAttention:
        return self._record(
            "worktree",
            _worktree_target_id(project, task_id),
            "response_completed",
            turn_id,
            None,
            now,
            session_id,
        )

    def complete_operator(
        self,
        operator_id: str,
        turn_id: str,
        now: datetime | None = None,
        session_id: str = "",
    ) -> ApprovalAttention:
        return self._record(
            "operator",
            operator_id,
            "response_completed",
            turn_id,
            None,
            now,
            session_id,
        )

    def clear(
        self,
        project: str,
        task_id: str,
        tool_name: str,
        turn_id: str,
        now: datetime | None = None,
        session_id: str = "",
    ) -> None:
        self._clear_permission(
            "worktree",
            _worktree_target_id(project, task_id),
            tool_name,
            turn_id,
            now,
            session_id,
        )

    def clear_operator_permission(
        self,
        operator_id: str,
        tool_name: str,
        turn_id: str,
        now: datetime | None = None,
        session_id: str = "",
    ) -> None:
        self._clear_permission(
            "operator", operator_id, tool_name, turn_id, now, session_id
        )

    def acknowledge(
        self, project: str, task_id: str, now: datetime | None = None
    ) -> tuple[ApprovalAttention, ...]:
        return self._acknowledge("worktree", _worktree_target_id(project, task_id), now)

    def acknowledge_operator(
        self, operator_id: str, now: datetime | None = None
    ) -> tuple[ApprovalAttention, ...]:
        return self._acknowledge("operator", operator_id, now)

    def clear_task(self, project: str, task_id: str) -> None:
        """Clear every event for a closed Agent session."""
        self._clear_target("worktree", _worktree_target_id(project, task_id))

    def clear_operator(self, operator_id: str) -> None:
        """Clear every event for a stopped Operation Terminal."""
        self._clear_target("operator", operator_id)

    def list(self, now: datetime | None = None) -> tuple[ApprovalAttention, ...]:
        current = _now() if now is None else now
        with self._lock:
            self._expire(current)
            return tuple(self._items.values())

    def _record(
        self,
        target: AttentionTarget,
        target_id: str,
        event: AttentionEvent,
        turn_id: str,
        tool_name: str | None,
        now: datetime | None,
        session_id: str,
    ) -> ApprovalAttention:
        requested_at = _now() if now is None else now
        item = ApprovalAttention(
            target=target,
            target_id=target_id,
            event=event,
            requested_at=requested_at,
            turn_id=turn_id,
            tool_name=tool_name,
            session_id=session_id,
        )
        with self._lock:
            self._expire(requested_at)
            self._items[(target, target_id, event)] = item
        return item

    def _clear_permission(
        self,
        target: AttentionTarget,
        target_id: str,
        tool_name: str,
        turn_id: str,
        now: datetime | None,
        session_id: str,
    ) -> None:
        current = _now() if now is None else now
        with self._lock:
            self._expire(current)
            key = (target, target_id, "permission_request")
            item = self._items.get(key)
            if item is not None and (item.session_id, item.tool_name, item.turn_id) == (
                session_id,
                tool_name,
                turn_id,
            ):
                del self._items[key]

    def _acknowledge(
        self, target: AttentionTarget, target_id: str, now: datetime | None
    ) -> tuple[ApprovalAttention, ...]:
        current = _now() if now is None else now
        with self._lock:
            self._expire(current)
            updated = [
                replace(item, acknowledged=True)
                for key, item in self._items.items()
                if key[:2] == (target, target_id)
            ]
            for item in updated:
                self._items[(item.target, item.target_id, item.event)] = item
            return tuple(updated)

    def _clear_target(self, target: AttentionTarget, target_id: str) -> None:
        with self._lock:
            self._items = {
                key: item
                for key, item in self._items.items()
                if key[:2] != (target, target_id)
            }

    def _expire(self, now: datetime) -> None:
        self._items = {
            key: item
            for key, item in self._items.items()
            if now - item.requested_at < ATTENTION_TTL
        }


def _worktree_target_id(project: str, task_id: str) -> str:
    return f"{project}/{task_id}"


def _now() -> datetime:
    return datetime.now(UTC)


approval_attention = ApprovalAttentionStore()
