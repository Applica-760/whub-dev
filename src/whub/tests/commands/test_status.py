"""`whub status` command rendering tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.status import status
from whub.models import ResourceStatus, StatusReport, WorktreeStatus


def _report(
    resources: tuple[ResourceStatus, ...] = (),
    invalid_worktrees: tuple[WorktreeStatus, ...] = (),
) -> StatusReport:
    return StatusReport(resources, invalid_worktrees)


def _context() -> SimpleNamespace:
    return SimpleNamespace(workspace_root="/workspace")


class TestStatusCommand:
    def test_renders_resource_report(self) -> None:
        report = _report(
            (
                ResourceStatus("local", "ok", "symlink"),
                ResourceStatus("remote", "ok", "remote", mount="ok"),
            )
        )
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_status", return_value=report),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "local" in result.output
        assert "remote" in result.output
        assert "symlink" in result.output

    def test_displays_no_resources_for_empty_report(self) -> None:
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_status", return_value=_report()),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "(no resources)" in result.output

    def test_fails_for_unhealthy_resource_report(self) -> None:
        report = _report((ResourceStatus("remote", "missing", "remote"),))
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_status", return_value=report),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code == 1

    def test_renders_worktree_summary_and_fails_for_diagnostics(self) -> None:
        worktree = WorktreeStatus(
            "local",
            "TASK-075",
            "tasks/075",
            "projects/worktrees/local-075",
            ("git worktree is missing: projects/worktrees/local-075",),
        )
        report = _report(
            (ResourceStatus("local", "ok", "symlink", worktrees=(worktree,)),)
        )
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.current_context", return_value=_context()),
            patch("whub.commands.status.collect_status", return_value=report),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code == 1
        assert "worktrees: 1 registered, 1 diagnostic" in result.output
        assert "local/TASK-075" in result.output
