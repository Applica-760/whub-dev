"""`whub vscode` command tests."""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.vscode import _build_settings, vscode
from whub.tests.helpers import manifest


class TestVscodeSpec:
    def test_builds_exclusions_for_symlink_and_mounted_remote(self) -> None:
        settings = _build_settings(manifest())

        paths = ["projects/local/**", "projects/remote/**"]
        assert settings == {
            "files.watcherExclude": {path: True for path in paths},
            "search.exclude": {path: True for path in paths},
            "python.analysis.exclude": paths,
        }

    def test_writes_settings_preserving_unmanaged_values(self, tmp_path) -> None:
        settings_path = tmp_path / ".vscode" / "settings.json"
        settings_path.parent.mkdir()
        settings_path.write_text(json.dumps({"editor.tabSize": 2}))

        with (
            patch("whub.commands.vscode.get_manifest", return_value=manifest()),
            patch("whub.commands.vscode.whub_root", return_value=tmp_path),
        ):
            first = CliRunner().invoke(vscode, catch_exceptions=False)
            second = CliRunner().invoke(vscode, catch_exceptions=False)

        assert first.exit_code == 0
        assert "write" in first.output
        assert second.exit_code == 0
        assert "skip" in second.output
        settings = json.loads(settings_path.read_text())
        assert settings["editor.tabSize"] == 2
        assert settings["files.watcherExclude"] == {
            "projects/local/**": True,
            "projects/remote/**": True,
        }
