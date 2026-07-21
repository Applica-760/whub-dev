"""`whub todo`コマンドのCLI振る舞いテスト。

検証するケース:
1. pending一覧表示（デフォルト）
2. -aで完了済みも表示
3. add正常系：serviceが入力を受け取る
4. add＋未知--project → エラー
5. add＋--project省略 → projectがNoneでserviceへ渡る
6. done正常系：serviceを呼ぶ
7. done＋未存在ID → エラー
8. done＋既完了 → エラー
9. rm正常系：serviceを呼ぶ
10. _parse_due_date：YYYY-MM-DD形式でdateを返す
11. _parse_due_date：MMDD形式で今年or翌年のdateを返す
12. _parse_due_date：不正値 → BadParameter

検証しないケース:
- 実際のファイルI/O（serviceでカバー）
- render_tableの描画詳細（test_renderでカバー）
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from whub.commands.todo import todo, _parse_due_date
from whub.models.todo import Todo, Todos
from whub.services.errors import NotFoundError, ServiceError
from whub.tests.helpers import manifest


def _make_todos(*items: Todo) -> Todos:
    return Todos(todos=list(items))


def _pending_todo(id: int = 1, **kwargs) -> Todo:
    defaults = dict(title=f"task-{id}", priority="none", created_at=date(2026, 1, 1))
    defaults.update(kwargs)
    return Todo(id=id, **defaults)


def _done_todo(id: int = 10, **kwargs) -> Todo:
    defaults = dict(
        title=f"done-{id}",
        priority="none",
        created_at=date(2026, 1, 1),
        done=True,
        done_at=date(2026, 1, 15),
    )
    defaults.update(kwargs)
    return Todo(id=id, **defaults)


class TestTodoCmdSpec:
    def test_list_pending(self):
        # ケース1
        items = [_pending_todo(1, title="buy milk")]
        with patch("whub.commands.todo.list_pending", return_value=items):
            result = CliRunner().invoke(todo, catch_exceptions=False)

        assert result.exit_code == 0
        assert "buy milk" in result.output

    def test_list_all_with_a_flag(self):
        # ケース2
        pending = [_pending_todo(1, title="pending-task")]
        completed = [_done_todo(2, title="completed-task")]
        with (
            patch("whub.commands.todo.list_pending", return_value=pending),
            patch("whub.commands.todo.list_completed", return_value=completed),
        ):
            result = CliRunner().invoke(todo, ["-a"], catch_exceptions=False)

        assert "pending-task" in result.output
        assert "completed-task" in result.output

    def test_add_creates_todo(self):
        # ケース3
        m = manifest()
        item = _pending_todo(1, title="new task", project="local", priority="red")
        with (
            patch("whub.commands.todo.get_manifest", return_value=m),
            patch("whub.commands.todo.add_todo", return_value=item) as mock_add,
        ):
            result = CliRunner().invoke(
                todo,
                ["add", "new task", "red", "--project", "local"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "added" in result.output
        mock_add.assert_called_once_with(m, "new task", "local", "red", None)

    def test_add_unknown_project_errors(self):
        # ケース4
        m = manifest()
        with (
            patch("whub.commands.todo.get_manifest", return_value=m),
            patch(
                "whub.commands.todo.add_todo",
                side_effect=ServiceError("unknown project: nonexistent"),
            ),
        ):
            result = CliRunner().invoke(
                todo,
                ["add", "task", "none", "--project", "nonexistent"],
            )

        assert result.exit_code != 0
        assert "unknown project" in result.output

    def test_add_without_project(self):
        # ケース5
        item = _pending_todo(1, title="orphan task", priority="blue")
        with (
            patch("whub.commands.todo.get_manifest", return_value=manifest()),
            patch("whub.commands.todo.add_todo", return_value=item) as mock_add,
        ):
            result = CliRunner().invoke(
                todo,
                ["add", "orphan task", "blue"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert mock_add.call_args.args[2] is None

    def test_done_marks_complete(self):
        # ケース6
        item = _done_todo(1, title="finish it")
        with patch(
            "whub.commands.todo.complete_todo", return_value=item
        ) as mock_complete:
            result = CliRunner().invoke(
                todo,
                ["done", "1"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "done" in result.output
        mock_complete.assert_called_once_with(1)

    def test_done_not_found_errors(self):
        # ケース7
        with patch(
            "whub.commands.todo.complete_todo",
            side_effect=NotFoundError("todo not found: 999"),
        ):
            result = CliRunner().invoke(todo, ["done", "999"])

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_done_already_done_errors(self):
        # ケース8
        with patch(
            "whub.commands.todo.complete_todo",
            side_effect=ServiceError("already done: 1"),
        ):
            result = CliRunner().invoke(todo, ["done", "1"])

        assert result.exit_code != 0
        assert "already done" in result.output

    def test_rm_removes_todo(self):
        # ケース9
        item = _pending_todo(1, title="remove me")
        with patch("whub.commands.todo.remove_todo", return_value=item) as mock_remove:
            result = CliRunner().invoke(
                todo,
                ["rm", "1"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "removed" in result.output
        mock_remove.assert_called_once_with(1)


class TestParseDueDateSpec:
    def test_iso_format(self):
        # ケース10
        result = _parse_due_date("2026-08-15")
        assert result == date(2026, 8, 15)

    def test_mmdd_format(self):
        # ケース11
        today = date(2026, 7, 7)
        assert _parse_due_date("0815", today=today) == date(2026, 8, 15)
        assert _parse_due_date("0707", today=today) == date(2026, 7, 7)
        assert _parse_due_date("0706", today=today) == date(2027, 7, 6)
        assert _parse_due_date("0101", today=today) == date(2027, 1, 1)

    def test_invalid_format_raises(self):
        # ケース12
        with pytest.raises(click.BadParameter):
            _parse_due_date("abc")
        with pytest.raises(click.BadParameter):
            _parse_due_date("13")
