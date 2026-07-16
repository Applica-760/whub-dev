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
    assert "transition" in result.output
    assert "apply" not in result.output


def test_task_check_accepts_a_task_path() -> None:
    # ケース3
    result = CliRunner().invoke(main, ["task", "check", str(_TASK_PATH)])

    assert result.exit_code == 0
    assert f"valid {_TASK_PATH}" in result.output


def test_task_check_resolves_a_task_id(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "example.yaml").write_text(_TASK_PATH.read_text())
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["task", "check", "001"])

    assert result.exit_code == 0
    assert "valid docs/tasks/example.yaml" in result.output


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


def test_task_graph_prints_task_dependencies_as_mermaid(tmp_path: Path) -> None:
    prerequisite = yaml.safe_load(_TASK_PATH.read_text())
    dependent = yaml.safe_load(_TASK_PATH.read_text())
    dependent["task"].update(
        id="TASK-003",
        title="depends on TASK-001",
        state="draft",
        depends_on=["TASK-001"],
    )
    dependent["approvals"] = []
    dependent["acceptance_results"] = []
    dependent["result"] = None
    for phase in dependent["plan"]["phases"]:
        phase["log"] = None
        for step in phase["steps"]:
            step["state"] = "pending"
    (tmp_path / "prerequisite.yaml").write_text(
        yaml.safe_dump(prerequisite, allow_unicode=True, sort_keys=False)
    )
    (tmp_path / "dependent.yaml").write_text(
        yaml.safe_dump(dependent, allow_unicode=True, sort_keys=False)
    )

    result = CliRunner().invoke(
        main,
        ["task", "graph", "--task-dir", str(tmp_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert result.output.startswith("flowchart TD\n")
    assert 'TASK_001["TASK-001:' in result.output
    assert 'TASK_003["TASK-003: depends on TASK-001"]' in result.output
    assert "TASK_001 --> TASK_003" in result.output


def test_task_graph_resolves_a_task_id_from_docs_tasks(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "example.yaml").write_text(_TASK_PATH.read_text())
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        main,
        ["task", "graph", "001"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert result.output.startswith("flowchart TD\n")
    assert 'phase_001["Phase 1: 現行手順の確認"]' in result.output
    assert "phase_001 --> phase_002" in result.output


def test_task_commands_update_a_task_record(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "docs/tasks/task.yaml"
    path.parent.mkdir(parents=True)
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
    monkeypatch.chdir(tmp_path)
    show = runner.invoke(main, ["task", "show", "001"], catch_exceptions=False)
    assert show.exit_code == 0
    assert "state: draft" in show.output
    assert "Phase 1: 現行手順の確認" in show.output
    assert "[001-001] [ ] 設定ファイルと既存ドキュメントから正しいセットアップ手順を確認する" in show.output

    approved = runner.invoke(
        main,
        ["task", "transition", "001", "approve_plan", "--actor", "user"],
        catch_exceptions=False,
    )
    assert approved.exit_code == 0

    done = runner.invoke(
        main,
        [
            "task",
            "done",
            "001",
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
        ["task", "skip", "001", "002-002", "--reason", "not needed"],
        catch_exceptions=False,
    )
    assert skipped.exit_code == 0
    accepted = runner.invoke(
        main,
        ["task", "accept", "001", "ACC-001", "--status", "passed"],
        catch_exceptions=False,
    )
    assert accepted.exit_code == 0

    updated = yaml.safe_load(path.read_text())
    assert updated["task"]["state"] == "in_progress"
    assert updated["plan"]["phases"][0]["log"]["summary"] == "current style located"
    assert updated["plan"]["phases"][1]["steps"][1]["skip_reason"] == "not needed"
    assert updated["acceptance_results"] == [{"acceptance": "ACC-001", "status": "passed", "evidence": []}]

    show = runner.invoke(main, ["task", "show", "001"], catch_exceptions=False)

    assert show.exit_code == 0
    assert "[001-001] [x] 設定ファイルと既存ドキュメントから正しいセットアップ手順を確認する" in show.output
    assert "- current style located" in show.output
    assert "[002-002] [-] READMEに記載した手順でテストを実行する" in show.output
    assert "- skipped: not needed" in show.output
    assert "ACC-" not in show.output
