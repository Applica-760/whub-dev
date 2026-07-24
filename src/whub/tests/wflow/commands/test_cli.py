"""wflow CLIの仕様テスト。

検証するケース:
1. 引数なしのcheckが組込みtask Workflowを検査する。
2. taskサブコマンドグループが提供される。
3. task checkが指定Taskを検査する。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import pytest
import yaml

from whub.core.context import WhubContext
from whub.models import Manifest
from whub.tests.helpers import manifest_data
from whub.wflow.cli import main


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


@pytest.fixture(autouse=True)
def default_whub_dev_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    def load_default() -> Manifest:
        data = manifest_data()
        data["projects"][0]["name"] = "whub-dev"
        data["projects"][0]["resource"]["source"] = str(Path.cwd())
        return Manifest.model_validate(data)

    monkeypatch.setattr("whub.wflow.commands.task.load_manifest", load_default)


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
    assert "--project" in result.output
    assert "transition" in result.output
    assert "apply" not in result.output


def test_task_check_accepts_a_task_path() -> None:
    # ケース3
    result = CliRunner().invoke(main, ["task", "check", str(_TASK_PATH)])

    assert result.exit_code == 0
    assert f"valid {_TASK_PATH}" in result.output


def test_task_check_reports_apple_double_path(tmp_path: Path, monkeypatch) -> None:
    sidecar = tmp_path / "docs/tasks/._task.yaml"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_bytes(b"\x00\x05\x16\x07AppleDouble")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["task", "check", str(sidecar)])

    assert result.exit_code == 1
    assert "AppleDouble metadata is not a Task YAML" in result.output
    assert "Traceback" not in result.output


def test_task_project_option_uses_project_root_and_restores_cwd(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    task_path = project_root / "docs/tasks/example.yaml"
    task_path.parent.mkdir(parents=True)
    task_path.write_text(_TASK_PATH.read_text())
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    loaded_manifest = Manifest.model_validate(data)
    invocation_root = tmp_path / "workspace-hub"
    invocation_root.mkdir()
    monkeypatch.chdir(invocation_root)

    with patch(
        "whub.wflow.commands.task.load_manifest",
        return_value=loaded_manifest,
    ):
        by_id = CliRunner().invoke(
            main,
            ["task", "--project", "local", "check", "001"],
            catch_exceptions=False,
        )
        by_path = CliRunner().invoke(
            main,
            [
                "task",
                "--project",
                "local",
                "check",
                "docs/tasks/example.yaml",
            ],
            catch_exceptions=False,
        )
        absolute_path = CliRunner().invoke(
            main,
            ["task", "--project", "local", "check", str(task_path)],
            catch_exceptions=False,
        )

    assert by_id.exit_code == 0
    assert by_path.exit_code == 0
    assert absolute_path.exit_code == 0
    assert Path.cwd() == invocation_root


def test_task_project_option_applies_to_init(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    loaded_manifest = Manifest.model_validate(data)
    monkeypatch.chdir(tmp_path)

    with patch(
        "whub.wflow.commands.task.load_manifest",
        return_value=loaded_manifest,
    ):
        result = CliRunner().invoke(
            main,
            ["task", "--project", "local", "init", "Project Task", "目的"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert len(list((project_root / "docs/tasks").glob("*.yaml"))) == 1
    assert not (tmp_path / "docs/tasks").exists()


def test_task_project_option_reports_project_resolution_errors(
    tmp_path: Path,
) -> None:
    loaded_manifest = Manifest.model_validate(manifest_data())

    with patch(
        "whub.wflow.commands.task.load_manifest",
        return_value=loaded_manifest,
    ):
        unknown = CliRunner().invoke(
            main,
            ["task", "--project", "missing", "ls"],
        )
        unavailable = CliRunner().invoke(
            main,
            ["task", "--project", "remote", "ls"],
        )
        no_resource = CliRunner().invoke(
            main,
            ["task", "--project", "no-resource", "ls"],
        )

    assert unknown.exit_code == 1
    assert "unknown project: missing" in unknown.output
    assert unavailable.exit_code == 1
    assert "project resource is not available: remote" in unavailable.output
    assert no_resource.exit_code == 1
    assert "project has no resource: no-resource" in no_resource.output


def test_task_project_option_supports_remote_and_task_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    hub_root = tmp_path / "workspace-hub"
    local_root = tmp_path / "local"
    remote_root = hub_root / "projects/remote"
    for root in (hub_root, local_root, remote_root):
        root.mkdir(parents=True)
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(local_root)
    context_dir = tmp_path / "task-context"
    context_dir.mkdir()
    context_dir.joinpath("config.toml").write_text(f'workspace_root = "{hub_root}"\n')
    context = WhubContext(context_dir)
    with patch(
        "whub.models.manifest.current_context",
        return_value=context,
    ):
        loaded_manifest = Manifest.model_validate(data)
    monkeypatch.chdir(hub_root)

    for root in (remote_root,):
        task_path = root / "docs/tasks/example.yaml"
        task_path.parent.mkdir(parents=True)
        task_path.write_text(_TASK_PATH.read_text())
    custom_task = local_root / "custom/tasks/example.yaml"
    custom_task.parent.mkdir(parents=True)
    custom_task.write_text(_TASK_PATH.read_text())

    with (
        patch(
            "whub.wflow.commands.task.load_manifest",
            return_value=loaded_manifest,
        ),
        patch(
            "whub.models.manifest.current_context",
            return_value=context,
        ),
    ):
        remote = CliRunner().invoke(
            main,
            ["task", "--project", "remote", "check", "001"],
            catch_exceptions=False,
        )
        task_dir = CliRunner().invoke(
            main,
            ["task", "--project", "local", "ls", "custom/tasks"],
            catch_exceptions=False,
        )

    assert remote.exit_code == 0
    assert task_dir.exit_code == 0
    assert "TASK-001" in task_dir.output


def test_task_init_creates_a_draft_with_repeated_approaches(
    tmp_path: Path, monkeypatch
) -> None:
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


def test_task_init_rejects_invalid_input_without_creating_yaml(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        main, ["task", "init", "", "目的"], catch_exceptions=False
    )

    assert result.exit_code == 1
    assert "invalid task input" in result.output
    assert list((tmp_path / "docs/tasks").glob("*.yaml")) == []


def test_task_update_replaces_header_fields_and_approaches(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(
        main, ["task", "init", "旧タイトル", "旧目的", "--approach", "旧方針"]
    ).exit_code == 0

    result = runner.invoke(
        main,
        [
            "task",
            "update",
            "001",
            "--title",
            "新タイトル",
            "--objective",
            "新目的",
            "--approach",
            "方針1",
            "--approach",
            "方針2",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    path = next((tmp_path / "docs/tasks").glob("*.yaml"))
    updated = yaml.safe_load(path.read_text())["task"]
    assert updated["title"] == "新タイトル"
    assert updated["objective"] == "新目的"
    assert updated["approach"] == ["方針1", "方針2"]
    cleared = runner.invoke(
        main, ["task", "update", "001", "--clear-approaches"], catch_exceptions=False
    )
    assert cleared.exit_code == 0
    assert yaml.safe_load(path.read_text())["task"]["approach"] == []


def test_task_plan_is_created_and_approved_only_through_cli(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    prerequisite_commands = [
        ["task", "init", "前提Task", "依存先を完了する"],
        ["task", "plan", "insert", "001", "前提Step", "--phase-title", "前提Phase"],
        ["task", "transition", "001", "approve_plan", "--actor", "user"],
        ["task", "done", "001", "--log", '{"記録":"前提を完了した"}'],
        ["task", "complete", "001", "--result", "前提完了"],
    ]
    for command in prerequisite_commands:
        result = runner.invoke(main, command, catch_exceptions=False)
        assert result.exit_code == 0, result.output

    plan_commands = [
        ["task", "init", "対象Task", "CLIだけで計画する", "--approach", "CLIを使う"],
        ["task", "plan", "insert", "002", "最初のStep", "--phase-title", "計画Phase"],
        ["task", "plan", "insert", "002", "次のStep", "--phase", "001"],
        ["task", "plan", "update", "002", "001", "実行Phase"],
        ["task", "depends", "add", "002", "TASK-001"],
        ["task", "acceptance", "add", "002", "Taskを検証する"],
        ["task", "acceptance", "add", "002", "Phaseを検証する", "--phase", "001"],
    ]
    for command in plan_commands:
        result = runner.invoke(main, command, catch_exceptions=False)
        assert result.exit_code == 0, result.output

    checked = runner.invoke(main, ["task", "check", "002"], catch_exceptions=False)
    approved = runner.invoke(
        main,
        ["task", "transition", "002", "approve_plan", "--actor", "user"],
        catch_exceptions=False,
    )

    assert checked.exit_code == 0
    assert "valid" in checked.output
    assert approved.exit_code == 0
    assert "in_progress" in approved.output
    active_path = next((tmp_path / "docs/tasks").glob("*.yaml"))
    active = yaml.safe_load(active_path.read_text())
    assert active["task"]["depends_on"] == ["TASK-001"]
    assert active["plan"]["phases"][0]["title"] == "実行Phase"
    assert [step["description"] for step in active["plan"]["phases"][0]["steps"]] == [
        "最初のStep",
        "次のStep",
    ]
    assert [criterion["id"] for criterion in active["plan"]["acceptance"]] == [
        "ACC-001"
    ]
    assert [
        criterion["id"] for criterion in active["plan"]["phases"][0]["acceptance"]
    ] == ["ACC-002"]


def test_task_plan_insert_and_delete_update_a_draft(
    tmp_path: Path, monkeypatch
) -> None:
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

    inserted = CliRunner().invoke(
        main,
        ["task", "plan", "insert", "001", "追加", "--after", "002-001"],
        catch_exceptions=False,
    )
    deleted = CliRunner().invoke(
        main, ["task", "plan", "delete", "001", "001-001"], catch_exceptions=False
    )
    named_phase = CliRunner().invoke(
        main,
        [
            "task",
            "plan",
            "insert",
            "001",
            "最初のStep",
            "--phase-title",
            "名前付きPhase",
        ],
        catch_exceptions=False,
    )
    selected_phase = CliRunner().invoke(
        main,
        ["task", "plan", "insert", "001", "追加Step", "--phase", "002"],
        catch_exceptions=False,
    )
    updated = CliRunner().invoke(
        main,
        ["task", "plan", "update", "001", "002-003", "更新済みStep"],
        catch_exceptions=False,
    )
    dependency_added = CliRunner().invoke(
        main,
        ["task", "depends", "add", "001", "TASK-002"],
        catch_exceptions=False,
    )
    task_acceptance = CliRunner().invoke(
        main,
        ["task", "acceptance", "add", "001", "Taskを検証する"],
        catch_exceptions=False,
    )
    phase_acceptance = CliRunner().invoke(
        main,
        ["task", "acceptance", "add", "001", "Phaseを検証する", "--phase", "001"],
        catch_exceptions=False,
    )
    acceptance_deleted = CliRunner().invoke(
        main,
        ["task", "acceptance", "delete", "001", "ACC-002"],
        catch_exceptions=False,
    )
    dependency_deleted = CliRunner().invoke(
        main,
        ["task", "depends", "delete", "001", "TASK-002"],
        catch_exceptions=False,
    )

    assert inserted.exit_code == 0
    assert deleted.exit_code == 0
    assert named_phase.exit_code == 0
    assert selected_phase.exit_code == 0
    assert updated.exit_code == 0
    assert dependency_added.exit_code == 0
    assert task_acceptance.exit_code == 0
    assert "ACC-002" in task_acceptance.output
    assert phase_acceptance.exit_code == 0
    assert "ACC-003" in phase_acceptance.output
    assert acceptance_deleted.exit_code == 0
    assert dependency_deleted.exit_code == 0
    updated = yaml.safe_load(path.read_text())
    assert updated["plan"]["phases"][1]["steps"][1]["description"] == "追加"
    assert updated["plan"]["phases"][1]["steps"][2]["description"] == "更新済みStep"
    assert updated["plan"]["phases"][2]["title"] == "名前付きPhase"
    assert updated["plan"]["phases"][0]["steps"][0]["deleted"] is True
    assert updated["task"]["depends_on"] == []
    assert [item["id"] for item in updated["plan"]["acceptance"]] == ["ACC-001"]
    assert updated["plan"]["phases"][0]["acceptance"][0]["id"] == "ACC-003"


def test_task_complete_archives_an_already_completed_task(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "docs/tasks/task.yaml"
    source.parent.mkdir(parents=True)
    source.write_text(_TASK_PATH.read_text())
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        main, ["task", "complete", "001"], catch_exceptions=False
    )

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


def test_task_check_reports_interruption_relationship_errors(
    tmp_path: Path, monkeypatch
) -> None:
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


def test_task_approve_plan_requires_completed_dependencies(
    tmp_path: Path, monkeypatch
) -> None:
    task_dir = tmp_path / "docs/tasks"
    task_dir.mkdir(parents=True)
    prerequisite = yaml.safe_load(_TASK_PATH.read_text())
    prerequisite["task"]["state"] = "in_progress"
    dependent = yaml.safe_load(_TASK_PATH.read_text())
    dependent["task"].update(id="TASK-002", state="draft", depends_on=["TASK-001"])
    dependent["approvals"] = []
    dependent["acceptance_results"] = []
    dependent["change_requests"] = []
    dependent["result"] = None
    for phase in dependent["plan"]["phases"]:
        phase["log"] = []
        for step in phase["steps"]:
            step["state"] = "pending"
    prerequisite_path = task_dir / "prerequisite.yaml"
    dependent_path = task_dir / "dependent.yaml"
    prerequisite_path.write_text(yaml.safe_dump(prerequisite, allow_unicode=True))
    dependent_path.write_text(yaml.safe_dump(dependent, allow_unicode=True))
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    incomplete = runner.invoke(
        main,
        ["task", "transition", "002", "approve_plan", "--actor", "user"],
        catch_exceptions=False,
    )
    assert incomplete.exit_code == 1
    assert "incomplete dependency: TASK-001" in incomplete.output

    prerequisite["task"]["state"] = "completed"
    prerequisite_path.write_text(yaml.safe_dump(prerequisite, allow_unicode=True))
    dependent["task"]["depends_on"] = ["TASK-999"]
    dependent_path.write_text(yaml.safe_dump(dependent, allow_unicode=True))
    missing = runner.invoke(
        main, ["task", "transition", "002", "approve_plan", "--actor", "user"]
    )
    assert missing.exit_code == 1
    assert "missing dependency: TASK-999" in missing.output

    dependent["task"]["depends_on"] = ["TASK-001"]
    dependent_path.write_text(yaml.safe_dump(dependent, allow_unicode=True))
    approved = runner.invoke(
        main,
        ["task", "transition", "002", "approve_plan", "--actor", "user"],
        catch_exceptions=False,
    )
    assert approved.exit_code == 0


def test_task_interrupt_and_resume_use_cross_task_validation(
    tmp_path: Path, monkeypatch
) -> None:
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
        [
            "task",
            "interrupt",
            "001",
            "002",
            "--reason",
            "urgent",
            "--task-dir",
            str(task_dir),
        ],
    )
    assert interrupted.exit_code == 0
    assert "interrupted TASK-001 with TASK-002" in interrupted.output

    blocked_resume = runner.invoke(
        main, ["task", "resume", "001", "--task-dir", str(task_dir)]
    )
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
    (task_dir / "child.yaml").write_text(
        yaml.safe_dump(started_child, allow_unicode=True)
    )

    resumable_show = runner.invoke(
        main, ["task", "show", "001"], catch_exceptions=False
    )
    assert resumable_show.exit_code == 0
    assert "resumable: yes" in resumable_show.output
    listing = runner.invoke(main, ["task", "ls"], catch_exceptions=False)
    assert listing.exit_code == 0
    assert "interruption_source" in listing.output
    assert "TASK-002" in listing.output

    resumed = runner.invoke(
        main, ["task", "resume", "001", "--task-dir", str(task_dir)]
    )
    assert resumed.exit_code == 0
    assert "resumed TASK-001" in resumed.output


def test_task_ls_uses_whub_dev_by_default(tmp_path: Path, monkeypatch) -> None:
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
    assert (
        "[001-001] [ ] 設定ファイルと既存ドキュメントから正しいセットアップ手順を確認する"
        in show.output
    )

    approved = runner.invoke(
        main,
        ["task", "transition", "001", "approve_plan", "--actor", "user"],
        catch_exceptions=False,
    )
    assert approved.exit_code == 0

    logged = runner.invoke(
        main,
        [
            "task",
            "log",
            "001",
            "001",
            "--log",
            '{"調査":"discussion finding"}',
            "--log",
            '{"調査":"second discussion"}',
        ],
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
            '{"確認":"current style located"}',
            "--log",
            '{"確認":"second finding"}',
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
        {"value": {"調査": "discussion finding"}, "deleted": False},
        {"value": {"調査": "second discussion"}, "deleted": False},
        {"value": {"確認": "current style located"}, "deleted": False},
        {"value": {"確認": "second finding"}, "deleted": False},
    ]
    assert updated["plan"]["phases"][1]["steps"][1]["skip_reason"] == "not needed"
    assert updated["acceptance_results"] == [
        {"acceptance": "ACC-001", "status": "passed", "evidence": []}
    ]

    show = runner.invoke(main, ["task", "show", "001"], catch_exceptions=False)

    assert show.exit_code == 0
    assert (
        "[001-001] [x] 設定ファイルと既存ドキュメントから正しいセットアップ手順を確認する"
        in show.output
    )
    assert "- [確認]: current style located" in show.output
    assert "- [確認]: second finding" in show.output
    assert "- [調査]: discussion finding" in show.output
    assert "[002-002] [-] READMEに記載した手順でテストを実行する" in show.output
    assert "- skipped: not needed" in show.output
    assert "ACC-" not in show.output
