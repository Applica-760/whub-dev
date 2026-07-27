"""`whub remote cleanup-appledouble` behavior."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from subprocess import CompletedProcess
import subprocess
import sys
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.remote.cleanup_appledouble import cleanup_appledouble
from whub.commands.remote.cli import remote
from whub.tests.helpers import manifest
from whub.utils.apple_double import APPLE_DOUBLE_MAGIC, APPLE_DOUBLE_PREFIX


def run_asset(root: Path, mode: str) -> subprocess.CompletedProcess[str]:
    script = files("whub").joinpath("assets", "cleanup_appledouble.py").read_text()
    return subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            mode,
            APPLE_DOUBLE_PREFIX,
            APPLE_DOUBLE_MAGIC.hex(),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


class TestCleanupAppleDoubleAsset:
    def test_list_only_reports_verified_sidecars(self, tmp_path: Path) -> None:
        (tmp_path / "nested").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / "._valid").write_bytes(APPLE_DOUBLE_MAGIC + b"metadata")
        (tmp_path / "nested" / "._nested").write_bytes(APPLE_DOUBLE_MAGIC)
        (tmp_path / "._not-appledouble").write_bytes(b"not AppleDouble")
        (tmp_path / "regular").write_bytes(APPLE_DOUBLE_MAGIC)
        (tmp_path / ".git" / "._ignored").write_bytes(APPLE_DOUBLE_MAGIC)

        result = run_asset(tmp_path, "--list")

        assert result.returncode == 0
        assert result.stdout.splitlines() == ["._valid", "nested/._nested"]
        assert (tmp_path / "._valid").exists()
        assert (tmp_path / "nested" / "._nested").exists()

    def test_apply_removes_only_verified_sidecars(self, tmp_path: Path) -> None:
        valid = tmp_path / "._valid"
        invalid = tmp_path / "._not-appledouble"
        valid.write_bytes(APPLE_DOUBLE_MAGIC + b"metadata")
        invalid.write_bytes(b"not AppleDouble")

        result = run_asset(tmp_path, "--apply")

        assert result.returncode == 0
        assert result.stdout.splitlines() == ["._valid"]
        assert not valid.exists()
        assert invalid.exists()


class TestCleanupAppleDoubleCommand:
    def test_is_registered_in_remote_group(self) -> None:
        result = CliRunner().invoke(remote, ["--help"])

        assert result.exit_code == 0
        assert "cleanup-appledouble" in result.output

    def test_remote_runs_asset_in_list_mode(self) -> None:
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.commands.remote.cleanup_appledouble.get_manifest", return_value=manifest()),
            patch("whub.commands.remote.cleanup_appledouble.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(
                cleanup_appledouble, ["remote"], catch_exceptions=False
            )

        assert result.exit_code == 0
        command = mock_run.call_args.args[0]
        assert command[0] == "ssh"
        assert "python3" in " ".join(command)
        assert "--list" in " ".join(command)
        assert APPLE_DOUBLE_MAGIC.hex() in " ".join(command)

    def test_apply_is_explicit(self) -> None:
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.commands.remote.cleanup_appledouble.get_manifest", return_value=manifest()),
            patch("whub.commands.remote.cleanup_appledouble.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(
                cleanup_appledouble, ["--apply", "remote"], catch_exceptions=False
            )

        assert result.exit_code == 0
        assert "--apply" in " ".join(mock_run.call_args.args[0])

    def test_local_project_errors(self) -> None:
        with patch(
            "whub.commands.remote.cleanup_appledouble.get_manifest",
            return_value=manifest(),
        ):
            result = CliRunner().invoke(cleanup_appledouble, ["local"])

        assert result.exit_code == 1
        assert "not a remote resource" in result.output
