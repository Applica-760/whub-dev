from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.worktree import worktree
from whub.models import WorktreeDefinition, WorktreeDefinitionRecord, WorktreeInspection
from whub.services.errors import ServiceError
from whub.tests.helpers import manifest


def _definition() -> WorktreeDefinition:
    return WorktreeDefinition(
        task_id="TASK-072",
        parent_project="local",
        branch="tasks/072",
    )


def _context(root: Path) -> SimpleNamespace:
    return SimpleNamespace(workspace_root=root)


def test_create_passes_project_and_task_to_service(tmp_path: Path) -> None:
    destination = tmp_path / "projects/worktrees/local-072"
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch(
            "whub.commands.worktree.create_project_worktree",
            return_value=destination,
        ) as create,
    ):
        result = CliRunner().invoke(worktree, ["create", "local", "072"])

    assert result.exit_code == 0
    assert "local" in result.output
    assert "TASK-072" in result.output
    assert "tasks/072" in result.output
    assert str(destination) in result.output
    create.assert_called_once_with(manifest(), tmp_path, "local", "TASK-072")


def test_check_renders_inspections_and_fails_for_diagnostics(tmp_path: Path) -> None:
    definition = _definition()
    inspection = WorktreeInspection(
        WorktreeDefinitionRecord(tmp_path / "local-072.yaml", definition),
        ("git worktree is missing: projects/worktrees/local-072",),
    )
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch("whub.commands.worktree.inspect_worktrees", return_value=[inspection]),
    ):
        result = CliRunner().invoke(worktree, ["check"])

    assert result.exit_code == 1
    assert "local" in result.output
    assert "TASK-072" in result.output
    assert "git worktree is missing" in result.output


def test_rejects_prefixed_task_number() -> None:
    result = CliRunner().invoke(worktree, ["create", "local", "TASK-072"])

    assert result.exit_code != 0
    assert "expected TTT" in result.output


def test_remove_selects_definition_by_project_and_task(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch("whub.commands.worktree.remove_project_worktree") as remove,
    ):
        result = CliRunner().invoke(worktree, ["remove", "local", "072"])

    assert result.exit_code == 0
    assert "removed local/TASK-072" in result.output
    remove.assert_called_once_with(manifest(), tmp_path, "local", "TASK-072")


def test_create_renders_service_errors(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch(
            "whub.commands.worktree.create_project_worktree",
            side_effect=ServiceError("task not found: local/TASK-072"),
        ),
    ):
        result = CliRunner().invoke(worktree, ["create", "local", "072"])

    assert result.exit_code != 0
    assert "task not found: local/TASK-072" in result.output


def test_pull_request_renders_url(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch(
            "whub.commands.worktree.create_project_pull_request",
            return_value="https://example/pr/72",
        ) as create,
    ):
        result = CliRunner().invoke(worktree, ["pull-request", "local", "072"])

    assert result.exit_code == 0
    assert "https://example/pr/72" in result.output
    create.assert_called_once_with(manifest(), tmp_path, "local", "TASK-072")


def test_pull_request_renders_service_errors(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch(
            "whub.commands.worktree.create_project_pull_request",
            side_effect=ServiceError("gh PR lookup failed: not logged in"),
        ),
    ):
        result = CliRunner().invoke(worktree, ["pull-request", "local", "072"])

    assert result.exit_code != 0
    assert "gh PR lookup failed: not logged in" in result.output


def test_merge_requires_method_and_passes_it_to_service(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch("whub.commands.worktree.merge_project_pull_request") as merge,
    ):
        missing = CliRunner().invoke(worktree, ["merge", "local", "072"])
        result = CliRunner().invoke(
            worktree, ["merge", "local", "072", "--method", "squash"]
        )

    assert missing.exit_code != 0
    assert "Missing option '--method'" in missing.output
    assert result.exit_code == 0
    assert "merged local/TASK-072" in result.output
    merge.assert_called_once_with(manifest(), tmp_path, "local", "TASK-072", "squash")


def test_merge_renders_service_errors(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value=manifest()),
        patch("whub.commands.worktree.current_context", return_value=_context(tmp_path)),
        patch(
            "whub.commands.worktree.merge_project_pull_request",
            side_effect=ServiceError("gh PR merge failed: review required"),
        ),
    ):
        result = CliRunner().invoke(
            worktree, ["merge", "local", "072", "--method", "merge"]
        )

    assert result.exit_code != 0
    assert "gh PR merge failed: review required" in result.output
