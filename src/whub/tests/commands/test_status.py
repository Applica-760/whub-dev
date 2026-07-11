"""`whub status`コマンドのCLI振る舞いテスト。

検証するケース:
1. local+remote混在テーブル出力
2. リソースなし → "(no resources)"
3. unhealthy状態でexit code 1
4. SSHプローブ失敗でunreachable
5. _parse_probeが正常出力を解析する
6. _parse_probeが不正行を無視する
7. local git取得失敗はfailed表示
8. remote git取得失敗はfailed表示

検証しないケース:
- 実際のSSH接続
- 実際のgit status実行
"""
from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.status import status, _parse_probe
from whub.core.health import ResourceHealth
from whub.models import GitInfo, Manifest
from whub.tests.helpers import manifest


def _stub_inspect_symlink(_resource):
    return ResourceHealth("ok")


def _stub_inspect_mount(_resource, _project_name):
    return ResourceHealth("ok")


class TestStatusSpec:
    def test_mixed_table_output(self):
        # ケース1
        m = manifest()
        probe_data = {0: ("ok", "3", "on"), 1: ("ok", "0", "-")}
        with (
            patch("whub.commands.status.get_manifest", return_value=m),
            patch("whub.commands.status.inspect_symlink", _stub_inspect_symlink),
            patch("whub.commands.status.inspect_mount", _stub_inspect_mount),
            patch("whub.commands.status._probe_host", return_value=probe_data),
            patch("whub.commands.status.subprocess.run", return_value=CompletedProcess([], 0, stdout="")),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "local" in result.output
        assert "remote" in result.output
        assert "symlink" in result.output

    def test_no_resources(self):
        # ケース2
        m = Manifest(projects=[])
        with patch("whub.commands.status.get_manifest", return_value=m):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert result.exit_code == 0
        assert "(no resources)" in result.output

    def test_unhealthy_exits_nonzero(self):
        # ケース3
        m = manifest()
        probe_data = {0: ("missing", "?", "-")}
        with (
            patch("whub.commands.status.get_manifest", return_value=m),
            patch("whub.commands.status.inspect_symlink", _stub_inspect_symlink),
            patch("whub.commands.status.inspect_mount", _stub_inspect_mount),
            patch("whub.commands.status._probe_host", return_value=probe_data),
            patch("whub.commands.status.subprocess.run", return_value=CompletedProcess([], 0, stdout="")),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code != 0

    def test_stale_mount_exits_nonzero(self):
        m = manifest()
        with (
            patch("whub.commands.status.get_manifest", return_value=m),
            patch("whub.commands.status.inspect_symlink", _stub_inspect_symlink),
            patch(
                "whub.commands.status.inspect_mount",
                return_value=ResourceHealth("stale"),
            ),
            patch("whub.commands.status._probe_host", return_value={0: ("ok", "0", "-")}),
        ):
            result = CliRunner().invoke(status)

        assert result.exit_code != 0
        assert "stale" in result.output

    def test_unreachable_on_probe_failure(self):
        # ケース4
        m = manifest()
        with (
            patch("whub.commands.status.get_manifest", return_value=m),
            patch("whub.commands.status.inspect_symlink", _stub_inspect_symlink),
            patch("whub.commands.status.inspect_mount", _stub_inspect_mount),
            patch("whub.commands.status._probe_host", return_value=None),
            patch("whub.commands.status.subprocess.run", return_value=CompletedProcess([], 0, stdout="")),
        ):
            result = CliRunner().invoke(status)

        assert "unreachable" in result.output

    def test_parse_probe_normal(self):
        # ケース5
        stdout = "R0 ok 3 on\nR1 missing ? -\n"
        parsed = _parse_probe(stdout)

        assert parsed[0] == ("ok", "3", "on")
        assert parsed[1] == ("missing", "?", "-")

    def test_parse_probe_ignores_invalid_lines(self):
        # ケース6
        stdout = "R0 ok 3 on\nbogus line\n\nR1 missing ?\n"
        parsed = _parse_probe(stdout)

        assert 0 in parsed
        assert 1 not in parsed

    def test_local_git_failure_displays_failed(self):
        # ケース7
        m = manifest()
        m.resolve_project("local").resource.git = GitInfo(url="git@example.com:local.git")
        with (
            patch("whub.commands.status.get_manifest", return_value=m),
            patch("whub.commands.status.inspect_symlink", _stub_inspect_symlink),
            patch("whub.commands.status.inspect_mount", _stub_inspect_mount),
            patch("whub.commands.status._probe_host", return_value={0: ("ok", "0", "-")}),
            patch("whub.commands.status.subprocess.run", return_value=CompletedProcess([], 1, stdout="")),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert "failed" in result.output

    def test_remote_git_failure_displays_failed(self):
        # ケース8
        m = manifest()
        m.resolve_project("remote").resource.git = GitInfo(url="git@example.com:remote.git")
        with (
            patch("whub.commands.status.get_manifest", return_value=m),
            patch("whub.commands.status.inspect_symlink", _stub_inspect_symlink),
            patch("whub.commands.status.inspect_mount", _stub_inspect_mount),
            patch("whub.commands.status._probe_host", return_value={0: ("ok", "?", "-")}),
            patch("whub.commands.status.subprocess.run", return_value=CompletedProcess([], 0, stdout="")),
        ):
            result = CliRunner().invoke(status, catch_exceptions=False)

        assert "failed" in result.output
