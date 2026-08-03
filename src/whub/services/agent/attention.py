"""Keep short-lived Agent approval attention for the local web app."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock


ATTENTION_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class ApprovalAttention:
    """One unresolved Codex permission request for a registered worktree."""

    project: str
    task_id: str
    tool_name: str
    turn_id: str
    requested_at: datetime
    acknowledged: bool = False


class ApprovalAttentionStore:
    """In-memory control-plane state for approval requests."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], ApprovalAttention] = {}
        self._lock = Lock()

    def request(
        self,
        project: str,
        task_id: str,
        tool_name: str,
        turn_id: str,
        now: datetime | None = None,
    ) -> ApprovalAttention:
        requested_at = _now() if now is None else now
        item = ApprovalAttention(project, task_id, tool_name, turn_id, requested_at)
        with self._lock:
            self._expire(requested_at)
            self._items[(project, task_id)] = item
        return item

    def clear(
        self,
        project: str,
        task_id: str,
        tool_name: str,
        turn_id: str,
        now: datetime | None = None,
    ) -> None:
        current = _now() if now is None else now
        with self._lock:
            self._expire(current)
            key = (project, task_id)
            item = self._items.get(key)
            if item is not None and (item.tool_name, item.turn_id) == (
                tool_name,
                turn_id,
            ):
                del self._items[key]

    def acknowledge(
        self, project: str, task_id: str, now: datetime | None = None
    ) -> ApprovalAttention | None:
        current = _now() if now is None else now
        with self._lock:
            self._expire(current)
            key = (project, task_id)
            item = self._items.get(key)
            if item is None:
                return None
            acknowledged = ApprovalAttention(
                item.project,
                item.task_id,
                item.tool_name,
                item.turn_id,
                item.requested_at,
                acknowledged=True,
            )
            self._items[key] = acknowledged
            return acknowledged

    def clear_task(self, project: str, task_id: str) -> None:
        """Clear every unresolved request for a closed Agent session."""
        with self._lock:
            self._items.pop((project, task_id), None)

    def list(self, now: datetime | None = None) -> tuple[ApprovalAttention, ...]:
        current = _now() if now is None else now
        with self._lock:
            self._expire(current)
            return tuple(self._items.values())

    def _expire(self, now: datetime) -> None:
        self._items = {
            key: item
            for key, item in self._items.items()
            if now - item.requested_at < ATTENTION_TTL
        }


def _now() -> datetime:
    return datetime.now(UTC)


approval_attention = ApprovalAttentionStore()
