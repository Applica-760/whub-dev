"""Todo service behavior tests.

検証するケース:
1. todoの採番・保存・一覧ソート・完了・削除
2. todoの未知project・未存在ID・既完了エラー
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import pytest

from whub.models.todo import Todo, Todos, load_todos, save_todos
from whub.services.errors import NotFoundError, ServiceError
from whub.services.todo import (
    add_todo,
    complete_todo,
    list_completed,
    list_pending,
    remove_todo,
)
from whub.tests.helpers import manifest


@pytest.fixture
def todo_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config_dir = tmp_path / ".whub"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWD", str(tmp_path))
    return config_dir / "todos.yaml"


def test_todo_operations_persist_and_sort(todo_file: Path) -> None:
    # ケース1
    del todo_file
    save_todos(
        Todos(
            todos=[
                Todo(id=2, title="later", priority="blue", created_at=date(2026, 1, 1)),
                Todo(
                    id=4,
                    title="done",
                    priority="none",
                    created_at=date(2026, 1, 1),
                    done=True,
                    done_at=date(2026, 1, 3),
                ),
                Todo(
                    id=1,
                    title="urgent",
                    priority="red",
                    created_at=date(2026, 1, 1),
                    due_date=date(2026, 1, 2),
                ),
            ]
        )
    )

    item = add_todo(manifest(), "new", "local", "yellow", date(2026, 1, 4))

    assert item.id == 5
    assert [todo.id for todo in list_pending()] == [1, 5, 2]
    assert [todo.id for todo in list_completed()] == [4]

    completed = complete_todo(item.id)
    assert completed.done is True
    assert completed.done_at == date.today()

    removed = remove_todo(2)
    assert removed.id == 2
    assert [todo.id for todo in load_todos().todos] == [4, 1, 5]


def test_todo_service_errors(todo_file: Path) -> None:
    # ケース2
    del todo_file
    with pytest.raises(ServiceError, match="unknown project: missing"):
        add_todo(manifest(), "new", "missing", "none", None)

    with pytest.raises(NotFoundError, match="todo not found: 99"):
        complete_todo(99)
    with pytest.raises(NotFoundError, match="todo not found: 99"):
        remove_todo(99)

    save_todos(
        Todos(
            todos=[
                Todo(
                    id=1,
                    title="done",
                    created_at=date(2026, 1, 1),
                    done=True,
                    done_at=date(2026, 1, 2),
                )
            ]
        )
    )
    with pytest.raises(ServiceError, match="already done: 1"):
        complete_todo(1)
