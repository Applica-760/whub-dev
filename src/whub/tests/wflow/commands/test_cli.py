"""wflow CLIの仕様テスト。

検証するケース:
1. 引数なしのcheckが組込みtask Workflowを検査する。
2. taskサブコマンドグループが提供される。
3. task checkが指定Taskを検査する。
"""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from whub.wflow.cli import main


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "docs/tasks/20260713_2236_whub-task-planning-task-example.yaml"


def test_check_uses_the_builtin_task_workflow() -> None:
    # ケース1
    result = CliRunner().invoke(main, ["check"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "valid WF-001: task-planning" in result.output


def test_task_command_group_is_available() -> None:
    # ケース2
    result = CliRunner().invoke(main, ["task", "--help"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Operate task execution records." in result.output


def test_task_check_validates_a_task_record() -> None:
    # ケース3
    result = CliRunner().invoke(main, ["task", "check", str(_TASK_PATH)])

    assert result.exit_code == 0
    assert f"valid {_TASK_PATH}" in result.output
