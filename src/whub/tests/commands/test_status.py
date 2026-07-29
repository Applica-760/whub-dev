"""`whub status` command rendering tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.status import status
from whub.models import WorktreeStatus
from whub.services.status import ResourceStatus


def _status(
    project: str,
    state: str = "ok",
    type: str = "symlink",
    mount: str = "-",
) -> ResourceStatus:
    return ResourceStatus(project, state, type, mount=mount)


def _context() -> SimpleNamespace:
    return SimpleNamespace(workspace_root="/workspace")


class TestStatusCommand:
    def test_renders_mixed_resources(self) -> None:
        statuses = [
            _status("local"),
            _status("remote", type="remote", mount="ok"),
        ]
        with (
            patch("whub.commands.status.get_manifest"),
            patch(
                "whub.commands.status.collect_resource_status",
                return_value=statuses,
            ),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_worktree_status", return_value=[]),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "local" in result.output
        assert "remote" in result.output
        assert "symlink" in result.output

    def test_displays_no_resources(self) -> None:
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.collect_resource_status", return_value=[]),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_worktree_status", return_value=[]),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "(no resources)" in result.output

    def test_unhealthy_resource_exits_nonzero(self) -> None:
        with (
            patch("whub.commands.status.get_manifest"),
            patch(
                "whub.commands.status.collect_resource_status",
                return_value=[_status("remote", state="missing", type="remote")],
            ),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_worktree_status", return_value=[]),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code != 0

    def test_stale_mount_exits_nonzero(self) -> None:
        with (
            patch("whub.commands.status.get_manifest"),
            patch(
                "whub.commands.status.collect_resource_status",
                return_value=[_status("remote", type="remote", mount="stale")],
            ),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_worktree_status", return_value=[]),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code != 0
        assert "stale" in result.output

    def test_slow_mount_exits_zero(self) -> None:
        # slowは正常系（高遅延の可視化のみ）
        with (
            patch("whub.commands.status.get_manifest"),
            patch(
                "whub.commands.status.collect_resource_status",
                return_value=[_status("remote", type="remote", mount="slow")],
            ),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_worktree_status", return_value=[]),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "slow" in result.output

    def test_renders_worktree_summary_and_fails_for_diagnostics(self) -> None:
        worktrees = [
            WorktreeStatus(
                "local", "TASK-072", "tasks/072", "projects/worktrees/local-072"
            ),
            WorktreeStatus(
                "local",
                "TASK-075",
                "tasks/075",
                "projects/worktrees/local-075",
                ("git worktree is missing: projects/worktrees/local-075",),
            ),
        ]
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.collect_resource_status", return_value=[]),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch(
                "whub.commands.status.collect_worktree_status", return_value=worktrees
            ),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code == 1
        assert "worktrees: 2 registered, 1 diagnostic" in result.output
        assert "local/TASK-075" in result.output
