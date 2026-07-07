"""`whub.models.todo`のモデル仕様テスト。

検証するケース:
1. `Todo`は正の`id`、空でない`title`、`created_at`を要求する。
2. `title`と`project`は前後空白をtrimし、空文字は拒否する。
3. `priority`は`red`/`yellow`/`blue`/`none`だけを許可し、既定値は`none`にする。
4. `done`と`done_at`は同時に成立し、片方だけの状態を拒否する。
5. `Todos.pending`と`Todos.completed`は`done`状態で分類する。
6. `Todos`は重複`id`を拒否する。

検証しないケース:
1. `todos.yaml`の読み書き。
2. `todo` CLIの追加・完了・削除操作。
3. due dateのCLI入力パース。
"""
from __future__ import annotations
from datetime import date
import pytest
from pydantic import ValidationError
from whub.models import Todo, Todos

def _todo(**overrides) -> Todo:
    data = {
        "id": 1,
        "title": "task",
        "created_at": date(2026, 7, 7),
    }
    data.update(overrides)
    return Todo.model_validate(data)


class TestTodoModelSpec:
    def test_todo_requires_positive_id_title_and_created_at(self) -> None:
        # ケース1
        assert _todo().id == 1

        for overrides in (
            {"id": 0},
            {"id": -1},
            {"title": ""},
            {"created_at": None},
        ):
            with pytest.raises(ValidationError):
                _todo(**overrides)

        with pytest.raises(ValidationError):
            Todo.model_validate({"id": 1, "title": "task"})

    def test_title_and_project_are_trimmed_and_empty_values_are_rejected(self) -> None:
        # ケース2
        item = _todo(title="  task  ", project="  project  ")
        assert item.title == "task"
        assert item.project == "project"

        for overrides in (
            {"title": "   "},
            {"project": "   "},
        ):
            with pytest.raises(ValidationError):
                _todo(**overrides)

    def test_priority_is_limited_and_defaults_to_none(self) -> None:
        # ケース3
        assert _todo().priority == "none"

        for priority in ("red", "yellow", "blue", "none"):
            assert _todo(priority=priority).priority == priority

        with pytest.raises(ValidationError):
            _todo(priority="green")

    def test_done_and_done_at_must_be_set_together(self) -> None:
        # ケース4
        done_at = date(2026, 7, 8)
        assert not _todo().done
        assert _todo(done=True, done_at=done_at).done

        for overrides in (
            {"done": True},
            {"done": False, "done_at": done_at},
        ):
            with pytest.raises(ValidationError):
                _todo(**overrides)

    def test_pending_and_completed_split_by_done_state(self) -> None:
        # ケース5
        pending = _todo(id=1)
        completed = _todo(id=2, done=True, done_at=date(2026, 7, 8))
        todos = Todos.model_validate({"todos": [pending, completed]})

        assert todos.pending == [pending]
        assert todos.completed == [completed]

    def test_duplicate_ids_are_rejected(self) -> None:
        # ケース6
        with pytest.raises(ValidationError, match="duplicate todo ids"):
            Todos.model_validate({"todos": [_todo(id=1), _todo(id=1, title="other")]})
