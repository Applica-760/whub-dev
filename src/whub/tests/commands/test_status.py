"""`whub status` command rendering tests."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.status import status
from whub.services.status import ResourceStatus


def _status(
    project: str,
    state: str = "ok",
    type: str = "symlink",
    mount: str = "-",
) -> ResourceStatus:
    return ResourceStatus(project, state, type, mount=mount)


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
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "slow" in result.output
