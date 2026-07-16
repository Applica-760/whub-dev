"""wflow CLIの仕様テスト。

検証するケース:
1. 引数なしのcheckが組込みtask Workflowを検査する。
2. taskサブコマンドグループが提供される。
3. task checkが指定Taskを検査する。
"""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import yaml

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


def test_task_ls_uses_docs_tasks_by_default(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "example.yaml").write_text(_TASK_PATH.read_text())

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(main, ["task", "ls"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "path" in result.output
    assert "example.yaml" in result.output
    assert "TASK-001" in result.output
    assert "\t" not in result.output


def test_task_commands_update_a_task_record(tmp_path: Path) -> None:
    path = tmp_path / "task.yaml"
    data = yaml.safe_load(_TASK_PATH.read_text())
    data["task"]["state"] = "draft"
    data["approvals"] = []
    data["acceptance_results"] = []
    data["change_requests"] = []
    data["result"] = None
    for phase in data["plan"]["phases"]:
        phase["log"] = None
        for step in phase["steps"]:
            step["state"] = "pending"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))

    runner = CliRunner()
    show = runner.invoke(main, ["task", "show", str(path)], catch_exceptions=False)
    assert show.exit_code == 0
    assert "state: draft" in show.output
    assert "ready transitions: approve_plan" in show.output

    approved = runner.invoke(
        main,
        ["task", "apply", str(path), "approve_plan", "--actor", "user"],
        catch_exceptions=False,
    )
    assert approved.exit_code == 0

    done = runner.invoke(
        main,
        [
            "task",
            "done",
            str(path),
            "STP-001-001",
            "--log",
            "current style located",
            "--evidence",
            "src/whub/webapp",
        ],
        catch_exceptions=False,
    )
    assert done.exit_code == 0
    skipped = runner.invoke(
        main,
        ["task", "skip", str(path), "STP-002-001", "--reason", "not needed"],
        catch_exceptions=False,
    )
    assert skipped.exit_code == 0
    accepted = runner.invoke(
        main,
        ["task", "accept", str(path), "ACC-001", "--status", "passed"],
        catch_exceptions=False,
    )
    assert accepted.exit_code == 0

    updated = yaml.safe_load(path.read_text())
    assert updated["task"]["state"] == "in_progress"
    assert updated["plan"]["phases"][0]["log"]["summary"] == "current style located"
    assert updated["plan"]["phases"][1]["steps"][0]["skip_reason"] == "not needed"
    assert updated["acceptance_results"] == [{"acceptance": "ACC-001", "status": "passed", "evidence": []}]
