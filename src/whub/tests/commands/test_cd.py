"""`whub cd`コマンドのCLI振る舞いテスト。

検証するケース:
1. localリソースでパスを出力
2. localリソース＋パス未存在 → エラー
3. remoteリソースで非TTY時にEXIT_SSH(100)を返す
4. 未知project → エラー
5. shell-initでzshスニペットを出力

検証しないケース:
- 実際のSSH接続
- os.execvpの実行
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from whub.commands.cd import cd, shell_init
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
