"""Task CLI tests for Hub-owned active storage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import pytest
import yaml

from whub.core.context import WhubContext
from whub.models import Manifest
from whub.services.manifest import ResolvedManifest, resolve_manifest
from whub.tests.helpers import manifest_data
from whub.wflow.cli import main


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


def _task_environment(
    tmp_path: Path,
) -> tuple[Path, Path, WhubContext, ResolvedManifest]:
    hub_root = tmp_path / "workspace-hub"
    project_root = tmp_path / "project"
    hub_root.mkdir()
    project_root.mkdir()
    context_dir = tmp_path / "task-context"
    context_dir.mkdir()
    context_dir.joinpath("config.toml").write_text(f'workspace_root = "{hub_root}"\n')
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    context = WhubContext(context_dir)
    return (
        hub_root,
        project_root,
        context,
        resolve_manifest(Manifest.model_validate(data), context.workspace_root),
    )


def _task_data(task_id: str, *, state: str = "completed") -> dict:
    data = yaml.safe_load(_TASK_PATH.read_text())
    data["task"]["id"] = task_id
    if state == "completed":
        return data
    data["task"]["state"] = state
    data["acceptance_results"] = []
    data["change_requests"] = []
    data["result"] = None
    for phase in data["plan"]["phases"]:
        phase["log"] = []
        for step in phase["steps"]:
            step["state"] = "pending"
    if state == "draft":
        data["approvals"] = []
    if state == "cancelled":
        data["cancellation"] = {"actor": "user", "reason": "superseded"}
    return data


def _write_task(root: Path, filename: str, data: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / filename
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    return path


def test_task_init_and_check_use_hub_storage(tmp_path: Path, monkeypatch) -> None:
    hub_root, project_root, _, manifest = _task_environment(tmp_path)
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        runner = CliRunner()
        initialized = runner.invoke(
            main,
            ["task", "--project", "local", "init", "Task", "Objective"],
            catch_exceptions=False,
        )
        checked = runner.invoke(
            main,
            ["task", "--project", "local", "check", "001"],
            catch_exceptions=False,
        )

    assert initialized.exit_code == 0, initialized.output
    assert checked.exit_code == 0, checked.output
    assert len(list((hub_root / "wflow/tasks/local").glob("*.yaml"))) == 1
    assert not (project_root / "docs/tasks").exists()


def test_task_init_uses_project_task_history_for_id_allocation(
    tmp_path: Path, monkeypatch
) -> None:
    hub_root, project_root, _, manifest = _task_environment(tmp_path)
    history_root = project_root / "docs/tasks"
    archive_root = history_root / "done"
    archive_root.mkdir(parents=True)
    archived = yaml.safe_load(_TASK_PATH.read_text())
    archived["task"]["id"] = "TASK-014"
    archive_root.joinpath("archived.yaml").write_text(
        yaml.safe_dump(archived, allow_unicode=True)
    )
    historical = yaml.safe_load(_TASK_PATH.read_text())
    historical["task"]["id"] = "TASK-015"
    history_root.joinpath("historical.yaml").write_text(
        yaml.safe_dump(historical, allow_unicode=True)
    )
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        result = CliRunner().invoke(
            main,
            ["task", "--project", "local", "init", "Task", "Objective"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output
    assert "initialized TASK-016:" in result.output


def test_task_init_stops_when_remote_project_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    hub_root, _, _, manifest = _task_environment(tmp_path)
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        result = CliRunner().invoke(
            main,
            ["task", "--project", "remote", "init", "Task", "Objective"],
            catch_exceptions=False,
        )

    assert result.exit_code != 0
    assert "project resource is not available: remote" in result.output
    assert not list((hub_root / "wflow/tasks/remote").glob("*.yaml"))


def test_task_terminal_transitions_archive_to_project(
    tmp_path: Path, monkeypatch
) -> None:
    hub_root, project_root, _, manifest = _task_environment(tmp_path)
    task_root = hub_root / "wflow/tasks/local"
    task_root.mkdir(parents=True)

    cancelled = yaml.safe_load(_TASK_PATH.read_text())
    cancelled["task"]["state"] = "in_progress"
    cancelled["acceptance_results"] = []
    cancelled["change_requests"] = []
    cancelled["result"] = None
    cancelled_source = task_root / "cancelled.yaml"
    cancelled_source.write_text(yaml.safe_dump(cancelled, allow_unicode=True))

    completed = yaml.safe_load(_TASK_PATH.read_text())
    completed["task"]["id"] = "TASK-002"
    completed_source = task_root / "completed.yaml"
    completed_source.write_text(yaml.safe_dump(completed, allow_unicode=True))
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        runner = CliRunner()
        cancelled_result = runner.invoke(
            main,
            [
                "task",
                "--project",
                "local",
                "transition",
                "001",
                "cancel_task",
                "--actor",
                "user",
                "--reason",
                "cancelled",
            ],
            catch_exceptions=False,
        )
        completed_result = runner.invoke(
            main,
            ["task", "--project", "local", "complete", "002"],
            catch_exceptions=False,
        )

    assert cancelled_result.exit_code == 0, cancelled_result.output
    assert not cancelled_source.exists()
    assert (project_root / "docs/tasks/done/cancelled/cancelled.yaml").exists()
    assert completed_result.exit_code == 0, completed_result.output
    assert not completed_source.exists()
    assert (project_root / "docs/tasks/done/completed.yaml").exists()


def test_cli_reads_archive_dependencies_as_one_task_set(
    tmp_path: Path, monkeypatch
) -> None:
    hub_root, project_root, _, manifest = _task_environment(tmp_path)
    active_root = hub_root / "wflow/tasks/local"
    archive_root = project_root / "docs/tasks/done"
    dependent = _task_data("TASK-122", state="draft")
    dependent["task"]["depends_on"] = ["TASK-120"]
    dependent_path = _write_task(active_root, "dependent.yaml", dependent)
    _write_task(archive_root, "completed.yaml", _task_data("TASK-120"))
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        runner = CliRunner()
        listed = runner.invoke(
            main, ["task", "--project", "local", "ls"], catch_exceptions=False
        )
        checked = runner.invoke(
            main,
            ["task", "--project", "local", "check", "120"],
            catch_exceptions=False,
        )
        shown = runner.invoke(
            main,
            ["task", "--project", "local", "show", "120"],
            catch_exceptions=False,
        )
        approved = runner.invoke(
            main,
            [
                "task",
                "--project",
                "local",
                "transition",
                "122",
                "approve_plan",
                "--actor",
                "user",
            ],
            catch_exceptions=False,
        )

    assert listed.exit_code == 0, listed.output
    assert "TASK-122" in listed.output
    assert "yes" in listed.output
    assert checked.exit_code == 0, checked.output
    assert shown.exit_code == 0, shown.output
    assert "state: completed" in shown.output
    assert approved.exit_code == 0, approved.output
    assert yaml.safe_load(dependent_path.read_text())["task"]["state"] == "in_progress"


@pytest.mark.parametrize(
    ("dependency", "setup", "message"),
    [
        ("TASK-999", "missing", "missing dependency: TASK-999"),
        ("TASK-120", "cancelled", "incomplete dependency: TASK-120 (cancelled)"),
        ("TASK-120", "duplicate", "duplicate task id: TASK-120"),
    ],
)
def test_approve_plan_rejects_unmet_archive_dependencies(
    tmp_path: Path,
    monkeypatch,
    dependency: str,
    setup: str,
    message: str,
) -> None:
    hub_root, project_root, _, manifest = _task_environment(tmp_path)
    active_root = hub_root / "wflow/tasks/local"
    archive_root = project_root / "docs/tasks/done"
    dependent = _task_data("TASK-122", state="draft")
    dependent["task"]["depends_on"] = [dependency]
    _write_task(active_root, "dependent.yaml", dependent)
    if setup == "cancelled":
        _write_task(
            archive_root, "cancelled.yaml", _task_data("TASK-120", state="cancelled")
        )
    elif setup == "duplicate":
        _write_task(active_root, "active-120.yaml", _task_data("TASK-120"))
        _write_task(archive_root, "archived-120.yaml", _task_data("TASK-120"))
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        result = CliRunner().invoke(
            main,
            [
                "task",
                "--project",
                "local",
                "transition",
                "122",
                "approve_plan",
                "--actor",
                "user",
            ],
            catch_exceptions=False,
        )

    assert result.exit_code != 0
    assert message in result.output


@pytest.mark.parametrize(
    "operation",
    [
        ["update", "120", "--title", "changed"],
        ["plan", "update", "120", "001", "changed"],
        ["depends", "add", "120", "TASK-999"],
        ["complete", "120"],
    ],
)
def test_mutations_never_target_archived_tasks(
    tmp_path: Path, monkeypatch, operation: list[str]
) -> None:
    hub_root, project_root, _, manifest = _task_environment(tmp_path)
    archive_path = _write_task(
        project_root / "docs/tasks/done",
        "completed.yaml",
        _task_data("TASK-120"),
    )
    original = archive_path.read_bytes()
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        result = CliRunner().invoke(
            main,
            ["task", "--project", "local", *operation],
            catch_exceptions=False,
        )

    assert result.exit_code != 0
    assert "task ID not found: TASK-120" in result.output
    assert archive_path.read_bytes() == original


def test_resume_reads_terminal_interruption_from_archive(
    tmp_path: Path, monkeypatch
) -> None:
    hub_root, project_root, _, manifest = _task_environment(tmp_path)
    parent = _task_data("TASK-122", state="paused")
    parent["task"].update(
        interruption_task_id="TASK-120",
        interruption_reason="urgent work",
    )
    child = _task_data("TASK-120")
    child["task"]["interruption_source_task_id"] = "TASK-122"
    parent_path = _write_task(hub_root / "wflow/tasks/local", "parent.yaml", parent)
    child_path = _write_task(project_root / "docs/tasks/done", "child.yaml", child)
    original_child = child_path.read_bytes()
    monkeypatch.chdir(hub_root)

    with patch(
        "whub.wflow.services.task.application.load_manifest", return_value=manifest
    ):
        result = CliRunner().invoke(
            main,
            ["task", "--project", "local", "resume", "122"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output
    resumed = yaml.safe_load(parent_path.read_text())
    assert resumed["task"]["state"] == "in_progress"
    assert resumed["task"]["interruption_task_id"] == "TASK-120"
    assert child_path.read_bytes() == original_child
