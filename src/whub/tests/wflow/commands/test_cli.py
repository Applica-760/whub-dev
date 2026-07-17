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
_TASK_PATH = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


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


def test_task_init_creates_a_draft_with_repeated_approaches(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        main,
        [
            "task",
            "init",
            "新しいTask",
            "目的",
            "--approach",
            "方針1",
            "--approach",
            "方針2",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "initialized TASK-001:" in result.output
    paths = list((tmp_path / "docs/tasks").glob("*_task-001.yaml"))
    assert len(paths) == 1
    created = yaml.safe_load(paths[0].read_text())
    assert created["task"] == {
        "id": "TASK-001",
        "state": "draft",
        "title": "新しいTask",
        "objective": "目的",
        "approach": ["方針1", "方針2"],
        "depends_on": [],
        "interruption_task_id": None,
        "interruption_reason": None,
        "interruption_source_task_id": None,
    }
    assert created["plan"] is None


def test_task_init_rejects_invalid_input_without_creating_yaml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["task", "init", "", "目的"], catch_exceptions=False)

    assert result.exit_code == 1
    assert "invalid task input" in result.output
    assert list((tmp_path / "docs/tasks").glob("*.yaml")) == []


def test_task_plan_insert_and_delete_update_a_draft(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    data = yaml.safe_load(_TASK_PATH.read_text())
    data["task"]["state"] = "draft"
    data["approvals"] = []
    data["acceptance_results"] = []
    data["change_requests"] = []
    data["result"] = None
    for phase in data["plan"]["phases"]:
        phase["log"] = []
        for step in phase["steps"]:
            step["state"] = "pending"
    path = task_dir / "task.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    monkeypatch.chdir(tmp_path)

    inserted = CliRunner().invoke(main, ["task", "plan", "insert", "001", "追加", "--after", "002-001"], catch_exceptions=False)
    deleted = CliRunner().invoke(main, ["task", "plan", "delete", "001", "001-001"], catch_exceptions=False)

    assert inserted.exit_code == 0
    assert deleted.exit_code == 0
    updated = yaml.safe_load(path.read_text())
    assert updated["plan"]["phases"][1]["steps"][1]["description"] == "追加"
    assert updated["plan"]["phases"][0]["steps"][0]["deleted"] is True


def test_task_complete_archives_an_already_completed_task(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "docs/tasks/task.yaml"
    source.parent.mkdir(parents=True)
    source.write_text(_TASK_PATH.read_text())
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["task", "complete", "001"], catch_exceptions=False)

    assert result.exit_code == 0
    assert not source.exists()
    assert (tmp_path / "docs/tasks/done/task.yaml").exists()


def test_task_check_resolves_a_task_id(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "example.yaml").write_text(_TASK_PATH.read_text())
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["task", "check", "001"])

    assert result.exit_code == 0
    assert "valid docs/tasks/example.yaml" in result.output


def test_task_check_reports_interruption_relationship_errors(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    parent = yaml.safe_load(_TASK_PATH.read_text())
    parent["task"].update(
        state="paused",
        interruption_task_id="TASK-002",
        interruption_reason="urgent issue",
    )
    child = yaml.safe_load(_TASK_PATH.read_text())
    child["task"].update(
        id="TASK-002",
        state="in_progress",
        interruption_source_task_id="TASK-999",
    )
    (task_dir / "parent.yaml").write_text(yaml.safe_dump(parent, allow_unicode=True))
    (task_dir / "child.yaml").write_text(yaml.safe_dump(child, allow_unicode=True))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["task", "check", "001"])

    assert result.exit_code == 1
    assert "interruption_link_mismatch" in result.output


def test_task_interrupt_and_resume_use_cross_task_validation(tmp_path: Path, monkeypatch) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    parent = yaml.safe_load(_TASK_PATH.read_text())
    parent["task"]["state"] = "in_progress"
    parent["result"] = None
    child = yaml.safe_load(_TASK_PATH.read_text())
    child["task"].update(id="TASK-002", state="draft")
    child["approvals"] = []
    child["acceptance_results"] = []
    child["change_requests"] = []
    child["result"] = None
    for phase in child["plan"]["phases"]:
        phase["log"] = []
        for step in phase["steps"]:
            step["state"] = "pending"
    (task_dir / "parent.yaml").write_text(yaml.safe_dump(parent, allow_unicode=True))
    (task_dir / "child.yaml").write_text(yaml.safe_dump(child, allow_unicode=True))
    monkeypatch.chdir(tmp_path)

    rejected = CliRunner().invoke(
        main,
        ["task", "transition", "001", "interrupt_task", "--actor", "agent"],
    )
    assert rejected.exit_code == 1
    assert "dedicated interruption command" in rejected.output

    runner = CliRunner()
    interrupted = runner.invoke(
        main,
        ["task", "interrupt", "001", "002", "--reason", "urgent", "--task-dir", str(task_dir)],
    )
    assert interrupted.exit_code == 0
    assert "interrupted TASK-001 with TASK-002" in interrupted.output

    blocked_resume = runner.invoke(main, ["task", "resume", "001", "--task-dir", str(task_dir)])
    assert blocked_resume.exit_code == 1
    assert "not terminal" in blocked_resume.output

    paused_show = runner.invoke(main, ["task", "show", "001"], catch_exceptions=False)
    assert paused_show.exit_code == 0
    assert "interruption task: TASK-002" in paused_show.output
    assert "interruption reason: urgent" in paused_show.output
    assert "resumable: no" in paused_show.output

    started_child = yaml.safe_load((task_dir / "child.yaml").read_text())
    started_child["task"]["state"] = "cancelled"
    started_child["cancellation"] = {"reason": "done", "actor": "user"}
    (task_dir / "child.yaml").write_text(yaml.safe_dump(started_child, allow_unicode=True))

    resumable_show = runner.invoke(main, ["task", "show", "001"], catch_exceptions=False)
    assert resumable_show.exit_code == 0
    assert "resumable: yes" in resumable_show.output
    listing = runner.invoke(main, ["task", "ls"], catch_exceptions=False)
    assert listing.exit_code == 0
    assert "interruption_source" in listing.output
    assert "TASK-002" in listing.output

    resumed = runner.invoke(main, ["task", "resume", "001", "--task-dir", str(task_dir)])
    assert resumed.exit_code == 0
    assert "resumed TASK-001" in resumed.output


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
        phase["log"] = []
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

    logged = runner.invoke(
        main,
        ["task", "log", "001", "001", "--log", "discussion finding", "--log", "second discussion"],
        catch_exceptions=False,
    )
    assert logged.exit_code == 0

    done = runner.invoke(
        main,
        [
            "task",
            "done",
            "001",
            "--log",
            "current style located",
            "--log",
            "second finding",
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
    assert updated["plan"]["phases"][0]["log"] == [
        "discussion finding",
        "second discussion",
        "current style located",
        "second finding",
    ]
    assert updated["plan"]["phases"][1]["steps"][1]["skip_reason"] == "not needed"
    assert updated["acceptance_results"] == [{"acceptance": "ACC-001", "status": "passed", "evidence": []}]

    show = runner.invoke(main, ["task", "show", "001"], catch_exceptions=False)

    assert show.exit_code == 0
    assert "[001-001] [x] 設定ファイルと既存ドキュメントから正しいセットアップ手順を確認する" in show.output
    assert "- current style located" in show.output
    assert "- second finding" in show.output
    assert "- discussion finding" in show.output
    assert "[002-002] [-] READMEに記載した手順でテストを実行する" in show.output
    assert "- skipped: not needed" in show.output
    assert "ACC-" not in show.output
