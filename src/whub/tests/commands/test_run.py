"""`whub run`コマンドのCLI振る舞いテスト。

検証するケース:
1. remoteリソースでsubprocess.runが正しいSSHコマンドで呼ばれる
2. localリソース → エラー（require_resource_type）
3. --ttyフラグがSSHコマンドに反映される
4. リモートのexit codeがそのまま返る

検証しないケース:
- 実際のSSH実行
"""
from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.run import run
from whub.tests.helpers import manifest


class TestRunSpec:
    def test_remote_builds_ssh_command(self):
        # ケース1
        m = manifest()
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.commands.run.get_manifest", return_value=m),
            patch("whub.commands.run.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(run, ["remote", "ls", "-la"], catch_exceptions=False)

        assert result.exit_code == 0
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ssh"
        assert any("home.example.com" in arg for arg in cmd)
        assert "ls -la" in " ".join(cmd)

    def test_local_resource_errors(self):
        # ケース2
        m = manifest()
        with patch("whub.commands.run.get_manifest", return_value=m):
            result = CliRunner().invoke(run, ["local", "ls"])

        assert result.exit_code != 0
        assert "not a remote resource" in result.output

    def test_tty_flag_adds_ssh_t(self):
        # ケース3
        m = manifest()
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.commands.run.get_manifest", return_value=m),
            patch("whub.commands.run.subprocess.run", mock_run),
        ):
            CliRunner().invoke(run, ["--tty", "remote", "htop"], catch_exceptions=False)

        cmd = mock_run.call_args[0][0]
        assert "-t" in cmd

    def test_exit_code_propagation(self):
        # ケース4
        m = manifest()
        mock_run = MagicMock(return_value=CompletedProcess([], 42))
        with (
            patch("whub.commands.run.get_manifest", return_value=m),
            patch("whub.commands.run.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(run, ["remote", "false"])

        assert result.exit_code == 42
