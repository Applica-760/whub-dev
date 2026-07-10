"""Service-layer behavior tests.

検証するケース:
1. todoの採番・保存・一覧ソート・完了・削除
2. todoの未知project・未存在ID・既完了エラー
3. local backlogの追記とマーカー不正エラー
4. remote backlogのSSH経由書込内容
5. local/remote backlogの読取とmount未済エラー
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from whub.models.todo import Todo, Todos, load_todos, save_todos
from whub.services.backlog import MARKERS, append_backlog, read_backlog
from whub.services.errors import NotFoundError, ServiceError
from whub.services.todo import (
    add_todo,
    complete_todo,
    list_completed,
    list_pending,
    remove_todo,
)
from whub.tests.helpers import manifest
from whub.utils.managed_block import format_block


@pytest.fixture
def todo_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "todos.yaml"

    def resolve_todo_path() -> Path:
        return path

    monkeypatch.setattr("whub.models.todo.todo_path", resolve_todo_path)
    return path


def test_todo_operations_persist_and_sort(todo_file: Path) -> None:
    # ケース1
    del todo_file
    save_todos(Todos(todos=[
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
    ]))

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

    save_todos(Todos(todos=[Todo(
        id=1,
        title="done",
        created_at=date(2026, 1, 1),
        done=True,
        done_at=date(2026, 1, 2),
    )]))
    with pytest.raises(ServiceError, match="already done: 1"):
        complete_todo(1)


def test_local_backlog_appends_and_validates_markers(tmp_path: Path) -> None:
    # ケース3
    m = manifest()
    resource = m.resolve_project("local")
    assert resource is not None
    assert resource.resource is not None
    resource.resource.source = str(tmp_path)
    backlog = tmp_path / "docs" / "backlog.md"
    backlog.parent.mkdir()
    backlog.write_text(format_block(MARKERS, "existing"))

    append_backlog(m, "local", "new memo")

    assert backlog.read_text() == format_block(MARKERS, "existing\n- new memo")

    backlog.write_text("no markers\n")
    with pytest.raises(ServiceError, match="markers are missing or duplicated"):
        append_backlog(m, "local", "another memo")


def test_remote_backlog_writes_marker_content() -> None:
    # ケース4
    content = format_block(MARKERS, "existing")

    def run_ssh(host, command: str, **kwargs) -> CompletedProcess[str]:
        del host, kwargs
        if "test -d" in command:
            return CompletedProcess([], 0)
        if "if test -f" in command:
            return CompletedProcess([], 0, stdout="file\n")
        if command.startswith("cat "):
            return CompletedProcess([], 0, stdout=content)
        if "cat >" in command:
            return CompletedProcess([], 0)
        raise AssertionError(f"unexpected SSH command: {command}")

    with patch("whub.services.backlog.run_ssh_command", side_effect=run_ssh) as mock_ssh:
        append_backlog(manifest(), "remote", "new memo")

    write = mock_ssh.call_args_list[-1]
    assert write.kwargs["input"] == format_block(MARKERS, "existing\n- new memo")


def test_read_local_backlog_returns_content_or_empty(tmp_path: Path) -> None:
    # ケース5
    m = manifest()
    project = m.resolve_project("local")
    assert project is not None
    assert project.resource is not None
    project.resource.source = str(tmp_path)

    assert read_backlog(m, "local") == ""

    backlog = tmp_path / "docs" / "backlog.md"
    backlog.parent.mkdir()
    backlog.write_text("local memo\n")

    assert read_backlog(m, "local") == "local memo\n"


def test_read_remote_backlog_uses_mounted_workspace(tmp_path: Path) -> None:
    # ケース5
    m = manifest()
    project = m.resolve_project("remote")
    assert project is not None
    assert project.resource is not None
    resource = project.resource
    resource._resolved_workspace_path = tmp_path / "remote-mount"

    with pytest.raises(ServiceError, match="remote workspace path is not available"):
        read_backlog(m, "remote")

    resource._resolved_workspace_path.mkdir()
    backlog = resource._resolved_workspace_path / "docs" / "backlog.md"
    backlog.parent.mkdir()
    backlog.write_text("remote memo\n")

    assert read_backlog(m, "remote") == "remote memo\n"
