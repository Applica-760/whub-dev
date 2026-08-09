"""Minimal Task CLI adapter tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from whub.cli import main
from whub.models import Manifest
from whub.services.manifest import resolve_manifest
from whub.tests.helpers import manifest_data


def _manifest(tmp_path: Path):
    hub_root = tmp_path / "workspace-hub"
    project_root = tmp_path / "project"
    hub_root.mkdir()
    project_root.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    return (
        resolve_manifest(Manifest.model_validate(data), hub_root),
        hub_root,
        project_root,
    )


def test_task_cli_creates_logs_and_archives_a_runtime_pair(tmp_path: Path) -> None:
    manifest, hub_root, project_root = _manifest(tmp_path)

    with patch("whub.commands.task.get_manifest", return_value=manifest):
        runner = CliRunner()
        initialized = runner.invoke(
            main,
            ["task", "--project", "local", "init", "Task", "Objective"],
            catch_exceptions=False,
        )
        started = runner.invoke(
            main, ["task", "--project", "local", "start", "001"], catch_exceptions=False
        )
        logged = runner.invoke(
            main,
            [
                "task",
                "--project",
                "local",
                "log",
                "001",
                "--log",
                '{"fact":"verified"}',
            ],
            catch_exceptions=False,
        )
        completed = runner.invoke(
            main,
            ["task", "--project", "local", "complete", "001"],
            catch_exceptions=False,
        )
        checked = runner.invoke(
            main, ["task", "--project", "local", "check", "001"], catch_exceptions=False
        )

    active_root = hub_root / "flow/tasks/local"
    archive_root = project_root / "docs/tasks/done"
    assert initialized.exit_code == 0, initialized.output
    assert started.exit_code == 0, started.output
    assert logged.exit_code == 0, logged.output
    assert completed.exit_code == 0, completed.output
    assert checked.exit_code == 0, checked.output
    assert not list(active_root.glob("*.yaml"))
    archived = next(archive_root.glob("*.yaml"))
    assert archived.with_suffix(".md").exists()
    assert "verified" in archived.with_suffix(".md").read_text()


def test_task_cli_does_not_accept_an_actor_option() -> None:
    result = CliRunner().invoke(
        main, ["task", "--project", "local", "start", "001", "--actor", "agent"]
    )

    assert result.exit_code != 0
    assert "No such option '--actor'" in result.output
