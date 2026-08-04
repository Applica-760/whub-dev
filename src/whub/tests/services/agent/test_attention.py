from datetime import UTC, datetime, timedelta

from whub.services.agent.codex.attention import ATTENTION_TTL, ApprovalAttentionStore


def test_attention_lifecycle_requires_matching_tool_and_turn() -> None:
    store = ApprovalAttentionStore()
    started = datetime(2026, 8, 3, tzinfo=UTC)

    store.request("whub-dev", "TASK-104", "Bash", "turn-1", started)
    store.clear("whub-dev", "TASK-104", "Bash", "turn-2", started)

    assert len(store.list(started)) == 1

    items = store.acknowledge("whub-dev", "TASK-104", started)
    assert len(items) == 1 and items[0].acknowledged

    store.clear("whub-dev", "TASK-104", "Bash", "turn-1", started)
    assert store.list(started) == ()


def test_attention_lifecycle_requires_matching_session() -> None:
    store = ApprovalAttentionStore()
    started = datetime(2026, 8, 3, tzinfo=UTC)

    store.request("whub-dev", "TASK-104", "Bash", "turn-1", started, "session-1")
    store.clear("whub-dev", "TASK-104", "Bash", "turn-1", started, "session-2")

    assert len(store.list(started)) == 1

    store.clear("whub-dev", "TASK-104", "Bash", "turn-1", started, "session-1")
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

    assert [item.target_id for item in store.list(started)] == ["vault/TASK-101"]


def test_permission_and_completed_events_are_independent_per_target() -> None:
    store = ApprovalAttentionStore()
    started = datetime(2026, 8, 3, tzinfo=UTC)

    store.request("whub-dev", "TASK-104", "Bash", "turn-1", started, "session-1")
    store.complete("whub-dev", "TASK-104", "turn-1", started, "session-1")
    store.clear("whub-dev", "TASK-104", "Bash", "turn-1", started, "session-1")

    items = store.list(started)
    assert [(item.target, item.event) for item in items] == [
        ("worktree", "response_completed")
    ]


def test_operator_ids_keep_events_separate_from_display_order() -> None:
    store = ApprovalAttentionStore()
    started = datetime(2026, 8, 3, tzinfo=UTC)

    store.request_operator("operator-1", "Bash", "turn-1", started)
    store.complete_operator("operator-3", "turn-3", started)
    acknowledged = store.acknowledge_operator("operator-3", started)

    assert [item.target_id for item in acknowledged] == ["operator-3"]
    assert [(item.target_id, item.acknowledged) for item in store.list(started)] == [
        ("operator-1", False),
        ("operator-3", True),
    ]
