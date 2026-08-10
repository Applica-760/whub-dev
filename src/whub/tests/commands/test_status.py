"""`whub status` command rendering tests."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.status import status
from whub.models import ResourceStatus


class TestStatusCommand:
    def test_renders_resource_report(self) -> None:
        statuses = [
                ResourceStatus("local", "ok", "symlink"),
                ResourceStatus("remote", "ok", "remote", mount="ok"),
            ]
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.collect_resource_status", return_value=statuses),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "local" in result.output
        assert "remote" in result.output
        assert "symlink" in result.output

    def test_displays_no_resources_for_empty_report(self) -> None:
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.collect_resource_status", return_value=[]),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "(no resources)" in result.output

    def test_fails_for_unhealthy_resource_report(self) -> None:
        statuses = [ResourceStatus("remote", "missing", "remote")]
        with (
            patch("whub.commands.status.get_manifest"),
            patch("whub.commands.status.collect_resource_status", return_value=statuses),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code == 1
