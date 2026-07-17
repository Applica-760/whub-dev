"""`whub cd`コマンドのCLI振る舞いテスト。

検証するケース:
1. localリソースでパスを出力
2. localリソース＋パス未存在 → エラー
3. remoteリソースで非TTY時にEXIT_SSH(100)を返す
4. remoteリソースでSSHを実行し、終了後に端末モードを復旧する
5. 未知project → エラー
6. shell-initでzshスニペットを出力

検証しないケース:
- 実際のSSH接続
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from whub.commands.cd import EXIT_SSH, _TERMINAL_RECOVERY, _cd_remote, cd, shell_init
from whub.tests.helpers import manifest


class TestCdSpec:
    def test_local_echoes_path(self, tmp_path):
        # ケース1
        m = manifest()
        local_resource = m.resolve_project("local").resource
        local_resource._resolved_workspace_path = tmp_path / "projects" / "local"
        local_resource._resolved_workspace_path.mkdir(parents=True)

        with patch("whub.commands.cd.get_manifest", return_value=m):
            result = CliRunner().invoke(cd, ["local"], catch_exceptions=False)

        assert result.exit_code == 0
        assert str(tmp_path / "projects" / "local") in result.output

    def test_local_rejects_missing_path(self, tmp_path):
        # ケース2
        m = manifest()
        local_resource = m.resolve_project("local").resource
        local_resource._resolved_workspace_path = tmp_path / "nonexistent"

        with patch("whub.commands.cd.get_manifest", return_value=m):
            result = CliRunner().invoke(cd, ["local"])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_remote_signals_ssh(self):
        # ケース3
        m = manifest()
        with patch("whub.commands.cd.get_manifest", return_value=m):
            result = CliRunner().invoke(cd, ["remote"])

        assert result.exit_code == 100

    def test_remote_runs_ssh_preserves_exit_code_and_recovers_terminal(self):
        m = manifest()
        resource = m.resolve_project("remote").resource
        output = TtyOutput()

        with (
            patch(
                "whub.commands.cd.subprocess.run",
                return_value=subprocess.CompletedProcess(["ssh"], 23),
            ) as run,
            patch("whub.commands.cd.sys.stdout", output),
            pytest.raises(SystemExit) as error,
        ):
            _cd_remote(resource, ("remote", False))

        assert error.value.code == 23
        run.assert_called_once()
        assert output.value == _TERMINAL_RECOVERY
        assert output.flushed

    def test_remote_recovers_terminal_when_ssh_raises(self):
        m = manifest()
        resource = m.resolve_project("remote").resource
        output = TtyOutput()

        with (
            patch("whub.commands.cd.subprocess.run", side_effect=OSError("ssh unavailable")),
            patch("whub.commands.cd.sys.stdout", output),
            pytest.raises(OSError, match="ssh unavailable"),
        ):
            _cd_remote(resource, ("remote", False))

        assert output.value == _TERMINAL_RECOVERY
        assert output.flushed

    def test_remote_does_not_start_ssh_without_tty(self):
        m = manifest()
        resource = m.resolve_project("remote").resource

        with (
            patch("whub.commands.cd.subprocess.run") as run,
            patch("whub.commands.cd.sys.stdout", NonTtyOutput()),
            pytest.raises(SystemExit) as error,
        ):
            _cd_remote(resource, ("remote", False))

        assert error.value.code == EXIT_SSH
        run.assert_not_called()

    def test_unknown_project_errors(self):
        # ケース4
        m = manifest()
        with patch("whub.commands.cd.get_manifest", return_value=m):
            result = CliRunner().invoke(cd, ["nonexistent"])

        assert result.exit_code == 1
        assert "unknown project" in result.output

    def test_shell_init_outputs_zsh_snippet(self):
        # ケース5
        result = CliRunner().invoke(shell_init, catch_exceptions=False)

        assert result.exit_code == 0
        assert "whub()" in result.output
        assert "builtin cd" in result.output


class TtyOutput:
    def __init__(self) -> None:
        self.value = ""
        self.flushed = False

    def isatty(self) -> bool:
        return True

    def write(self, value: str) -> None:
        self.value += value

    def flush(self) -> None:
        self.flushed = True


class NonTtyOutput:
    def isatty(self) -> bool:
        return False
