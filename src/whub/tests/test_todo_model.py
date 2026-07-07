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
import unittest
from datetime import date
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


class TodoModelSpecTest(unittest.TestCase):
    def test_todo_requires_positive_id_title_and_created_at(self) -> None:
        # ケース1
        self.assertEqual(_todo().id, 1)

        for overrides in (
            {"id": 0},
            {"id": -1},
            {"title": ""},
            {"created_at": None},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValidationError):
                    _todo(**overrides)

        with self.assertRaises(ValidationError):
            Todo.model_validate({"id": 1, "title": "task"})

    def test_title_and_project_are_trimmed_and_empty_values_are_rejected(self) -> None:
        # ケース2
        item = _todo(title="  task  ", project="  project  ")
        self.assertEqual(item.title, "task")
        self.assertEqual(item.project, "project")

        for overrides in (
            {"title": "   "},
            {"project": "   "},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValidationError):
                    _todo(**overrides)

    def test_priority_is_limited_and_defaults_to_none(self) -> None:
        # ケース3
        self.assertEqual(_todo().priority, "none")

        for priority in ("red", "yellow", "blue", "none"):
            with self.subTest(priority=priority):
                self.assertEqual(_todo(priority=priority).priority, priority)

        with self.assertRaises(ValidationError):
            _todo(priority="green")

    def test_done_and_done_at_must_be_set_together(self) -> None:
        # ケース4
        done_at = date(2026, 7, 8)
        self.assertFalse(_todo().done)
        self.assertTrue(_todo(done=True, done_at=done_at).done)

        for overrides in (
            {"done": True},
            {"done": False, "done_at": done_at},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValidationError):
                    _todo(**overrides)

    def test_pending_and_completed_split_by_done_state(self) -> None:
        # ケース5
        pending = _todo(id=1)
        completed = _todo(id=2, done=True, done_at=date(2026, 7, 8))
        todos = Todos.model_validate({"todos": [pending, completed]})

        self.assertEqual(todos.pending, [pending])
        self.assertEqual(todos.completed, [completed])

    def test_duplicate_ids_are_rejected(self) -> None:
        # ケース6
        with self.assertRaisesRegex(ValidationError, "duplicate todo ids"):
            Todos.model_validate({"todos": [_todo(id=1), _todo(id=1, title="other")]})


if __name__ == "__main__":
    unittest.main()
