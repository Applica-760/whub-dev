"""Task CLI tests for Hub-owned active storage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
import yaml

from whub.core.context import WhubContext
from whub.models import Manifest
from whub.services.manifest import resolve_manifest
from whub.tests.helpers import manifest_data
from whub.wflow.cli import main


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


def _task_environment(tmp_path: Path) -> tuple[Path, Path, WhubContext, Manifest]:
    hub_root = tmp_path / "workspace-hub"
    project_root = tmp_path / "project"
    hub_root.mkdir()
    project_root.mkdir()
    context_dir = tmp_path / "task-context"
    context_dir.mkdir()
    context_dir.joinpath("config.toml").write_text(
        f'workspace_root = "{hub_root}"\n'
    )
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    context = WhubContext(context_dir)
    return (
        hub_root,
        project_root,
        context,
        resolve_manifest(Manifest.model_validate(data), context.workspace_root),
    )


def test_task_init_and_check_use_hub_storage(tmp_path: Path, monkeypatch) -> None:
    hub_root, project_root, context, manifest = _task_environment(tmp_path)
    monkeypatch.chdir(hub_root)

    with (
        patch("whub.wflow.commands.task.load_manifest", return_value=manifest),
        patch("whub.services.task.current_context", return_value=context),
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
    hub_root, project_root, context, manifest = _task_environment(tmp_path)
    history_root = project_root / "docs/tasks/done"
    history_root.mkdir(parents=True)
    archived = yaml.safe_load(_TASK_PATH.read_text())
    archived["task"]["id"] = "TASK-014"
    history_root.joinpath("archived.yaml").write_text(
        yaml.safe_dump(archived, allow_unicode=True)
    )
    monkeypatch.chdir(hub_root)

    with (
        patch("whub.wflow.commands.task.load_manifest", return_value=manifest),
        patch("whub.services.task.current_context", return_value=context),
    ):
        result = CliRunner().invoke(
            main,
            ["task", "--project", "local", "init", "Task", "Objective"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output
    assert "initialized TASK-015:" in result.output


def test_task_init_stops_when_remote_project_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    hub_root, _, context, manifest = _task_environment(tmp_path)
    monkeypatch.chdir(hub_root)

    with (
        patch("whub.wflow.commands.task.load_manifest", return_value=manifest),
        patch("whub.services.task.current_context", return_value=context),
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
    hub_root, project_root, context, manifest = _task_environment(tmp_path)
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

    with (
        patch("whub.wflow.commands.task.load_manifest", return_value=manifest),
        patch("whub.services.task.current_context", return_value=context),
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
