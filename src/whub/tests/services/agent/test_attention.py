from datetime import UTC, datetime, timedelta

from whub.services.agent.attention import ATTENTION_TTL, ApprovalAttentionStore


def test_attention_lifecycle_requires_matching_tool_and_turn() -> None:
    store = ApprovalAttentionStore()
    started = datetime(2026, 8, 3, tzinfo=UTC)

    store.request("whub-dev", "TASK-104", "Bash", "turn-1", started)
    store.clear("whub-dev", "TASK-104", "Bash", "turn-2", started)

    assert len(store.list(started)) == 1

    item = store.acknowledge("whub-dev", "TASK-104", started)
    assert item is not None and item.acknowledged

    store.clear("whub-dev", "TASK-104", "Bash", "turn-1", started)
    assert store.list(started) == ()


def test_attention_expires_after_ten_minutes() -> None:
    store = ApprovalAttentionStore()
    started = datetime(2026, 8, 3, tzinfo=UTC)

    store.request("whub-dev", "TASK-104", "Bash", "turn-1", started)

    assert store.list(started + ATTENTION_TTL - timedelta(microseconds=1))
    assert store.list(started + ATTENTION_TTL) == ()


def test_clear_task_removes_acknowledged_and_unacknowledged_attention() -> None:
    store = ApprovalAttentionStore()
    started = datetime(2026, 8, 3, tzinfo=UTC)
    store.request("whub-dev", "TASK-104", "Bash", "turn-1", started)
    store.acknowledge("whub-dev", "TASK-104", started)
    store.request("vault", "TASK-101", "Bash", "turn-2", started)

    store.clear_task("whub-dev", "TASK-104")

    assert [item.task_id for item in store.list(started)] == ["TASK-101"]
