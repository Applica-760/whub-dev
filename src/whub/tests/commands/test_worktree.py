from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.worktree import worktree


def _context(root: Path) -> SimpleNamespace:
    return SimpleNamespace(workspace_root=root)


def test_open_passes_auth_and_attaches_tmux(tmp_path: Path) -> None:
    session = SimpleNamespace(
        attach_command=("tmux", "attach-session", "-t", "worktree")
    )
    with (
        patch("whub.commands.worktree.get_manifest", return_value="manifest"),
        patch(
            "whub.commands.worktree.current_context", return_value=_context(tmp_path)
        ),
        patch(
            "whub.commands.worktree.open_project_worktree", return_value=session
        ) as open_worktree,
        patch("whub.commands.worktree.os.execvp") as attach,
    ):
        result = CliRunner().invoke(
            worktree, ["open", "local", "072", "--auth", "implementer"]
        )

    assert result.exit_code == 0
    open_worktree.assert_called_once_with(
        "manifest", tmp_path, "local", "TASK-072", ("implementer",)
    )
    attach.assert_called_once_with("tmux", ["tmux", "attach-session", "-t", "worktree"])


def test_close_merges_then_reports_url(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value="manifest"),
        patch(
            "whub.commands.worktree.current_context", return_value=_context(tmp_path)
        ),
        patch(
            "whub.commands.worktree.close_project_worktree",
            return_value="https://example/pr/72",
        ) as close_worktree,
    ):
        result = CliRunner().invoke(worktree, ["close", "local", "072"])

    assert result.exit_code == 0
    assert "merged local/TASK-072: https://example/pr/72" in result.output
    close_worktree.assert_called_once_with("manifest", tmp_path, "local", "TASK-072")


def test_pr_reports_url_without_merging(tmp_path: Path) -> None:
    with (
        patch("whub.commands.worktree.get_manifest", return_value="manifest"),
        patch(
            "whub.commands.worktree.current_context", return_value=_context(tmp_path)
        ),
        patch(
            "whub.commands.worktree.create_project_pull_request",
            return_value="https://example/pr/72",
        ) as create_pr,
    ):
        result = CliRunner().invoke(worktree, ["pr", "local", "072"])

    assert result.exit_code == 0
    assert "pull request local/TASK-072: https://example/pr/72" in result.output
    create_pr.assert_called_once_with("manifest", tmp_path, "local", "TASK-072")


def test_rejects_prefixed_task_number() -> None:
    result = CliRunner().invoke(worktree, ["close", "local", "TASK-072"])

    assert result.exit_code != 0
    assert "expected TTT" in result.output
