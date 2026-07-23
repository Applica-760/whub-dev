"""`whub ls` command rendering tests."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from whub.cli import main
from whub.models import Manifest
from whub.tests.helpers import manifest


class TestLsCommand:
    def test_lists_projects_and_resources(self) -> None:
        with patch("whub.commands.ls.get_manifest", return_value=manifest()):
            result = CliRunner().invoke(main, ["ls"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "project" in result.output
        assert "type" in result.output
        assert "workspace_path" in result.output
        assert "local" in result.output
        assert "symlink" in result.output
        assert "projects/local" in result.output
        assert "remote" in result.output
        assert "projects/remote" in result.output
        assert "no-resource  -        -" in result.output

    def test_displays_no_projects(self) -> None:
        with patch(
            "whub.commands.ls.get_manifest",
            return_value=Manifest(projects=[]),
        ):
            result = CliRunner().invoke(main, ["ls"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "(no projects)" in result.output
