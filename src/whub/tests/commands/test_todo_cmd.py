"""`whub todo`コマンドのCLI振る舞いテスト。

検証するケース:
1. pending一覧表示（デフォルト）
2. -aで完了済みも表示
3. add正常系：save_todosが新todo付きで呼ばれる
4. add＋未知project → エラー
5. add＋project=none → project_nameがNoneで保存
6. done正常系：done=True, done_at設定
7. done＋未存在ID → エラー
8. done＋既完了 → エラー
9. rm正常系：todosからitem削除
10. _parse_due_date：YYYY-MM-DD形式でdateを返す
11. _parse_due_date：MMDD形式で今年or翌年のdateを返す
12. _parse_due_date：不正値 → BadParameter

検証しないケース:
- 実際のファイルI/O（load_todos/save_todos mock）
- render_tableの描画詳細（test_renderでカバー）
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from whub.commands.todo import todo, _parse_due_date
from whub.models.todo import Todo, Todos
from whub.tests.helpers import manifest


def _make_todos(*items: Todo) -> Todos:
    return Todos(todos=list(items))


def _pending_todo(id: int = 1, **kwargs) -> Todo:
    defaults = dict(title=f"task-{id}", priority="none", created_at=date(2026, 1, 1))
    defaults.update(kwargs)
    return Todo(id=id, **defaults)


def _done_todo(id: int = 10, **kwargs) -> Todo:
    defaults = dict(
        title=f"done-{id}", priority="none", created_at=date(2026, 1, 1),
        done=True, done_at=date(2026, 1, 15),
    )
    defaults.update(kwargs)
    return Todo(id=id, **defaults)


class TestTodoCmdSpec:
    def test_list_pending(self):
        # ケース1
        todos = _make_todos(_pending_todo(1, title="buy milk"))
        with patch("whub.commands.todo.load_todos", return_value=todos):
            result = CliRunner().invoke(todo, catch_exceptions=False)

        assert result.exit_code == 0
        assert "buy milk" in result.output

    def test_list_all_with_a_flag(self):
        # ケース2
        todos = _make_todos(
            _pending_todo(1, title="pending-task"),
            _done_todo(2, title="completed-task"),
        )
        with patch("whub.commands.todo.load_todos", return_value=todos):
            result = CliRunner().invoke(todo, ["-a"], catch_exceptions=False)

        assert "pending-task" in result.output
        assert "completed-task" in result.output

    def test_add_creates_todo(self):
        # ケース3
        todos = _make_todos()
        m = manifest()
        mock_save = MagicMock()
        with (
            patch("whub.commands.todo.load_todos", return_value=todos),
            patch("whub.commands.todo.save_todos", mock_save),
            patch("whub.commands.todo.get_manifest", return_value=m),
        ):
            result = CliRunner().invoke(
                todo, ["add", "new task", "local", "red"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "added" in result.output
        saved = mock_save.call_args[0][0]
        assert len(saved.todos) == 1
        assert saved.todos[0].title == "new task"
        assert saved.todos[0].project == "local"

    def test_add_unknown_project_errors(self):
        # ケース4
        todos = _make_todos()
        m = manifest()
        with (
            patch("whub.commands.todo.load_todos", return_value=todos),
            patch("whub.commands.todo.get_manifest", return_value=m),
        ):
            result = CliRunner().invoke(todo, ["add", "task", "nonexistent", "none"])

        assert result.exit_code != 0
        assert "unknown project" in result.output

    def test_add_none_project(self):
        # ケース5
        todos = _make_todos()
        mock_save = MagicMock()
        with (
            patch("whub.commands.todo.load_todos", return_value=todos),
            patch("whub.commands.todo.save_todos", mock_save),
        ):
            result = CliRunner().invoke(
                todo, ["add", "orphan task", "none", "blue"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        saved = mock_save.call_args[0][0]
        assert saved.todos[0].project is None

    def test_done_marks_complete(self):
        # ケース6
        item = _pending_todo(1, title="finish it")
        todos = _make_todos(item)
        mock_save = MagicMock()
        with (
            patch("whub.commands.todo.load_todos", return_value=todos),
            patch("whub.commands.todo.save_todos", mock_save),
        ):
            result = CliRunner().invoke(
                todo, ["done", "1"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "done" in result.output
        assert item.done is True
        assert item.done_at is not None

    def test_done_not_found_errors(self):
        # ケース7
        todos = _make_todos()
        with patch("whub.commands.todo.load_todos", return_value=todos):
            result = CliRunner().invoke(todo, ["done", "999"])

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_done_already_done_errors(self):
        # ケース8
        todos = _make_todos(_done_todo(1))
        with patch("whub.commands.todo.load_todos", return_value=todos):
            result = CliRunner().invoke(todo, ["done", "1"])

        assert result.exit_code != 0
        assert "already done" in result.output

    def test_rm_removes_todo(self):
        # ケース9
        todos = _make_todos(_pending_todo(1, title="remove me"))
        mock_save = MagicMock()
        with (
            patch("whub.commands.todo.load_todos", return_value=todos),
            patch("whub.commands.todo.save_todos", mock_save),
        ):
            result = CliRunner().invoke(
                todo, ["rm", "1"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "removed" in result.output
        saved = mock_save.call_args[0][0]
        assert len(saved.todos) == 0


class TestParseDueDateSpec:
    def test_iso_format(self):
        # ケース10
        result = _parse_due_date("2026-08-15")
        assert result == date(2026, 8, 15)

    def test_mmdd_format(self):
        # ケース11
        today = date(2026, 7, 7)
        assert _parse_due_date("0815", today=today) == date(2026, 8, 15)
        assert _parse_due_date("0101", today=today) == date(2027, 1, 1)

    def test_invalid_format_raises(self):
        # ケース12
        with pytest.raises(click.BadParameter):
            _parse_due_date("abc")
        with pytest.raises(click.BadParameter):
            _parse_due_date("13")
