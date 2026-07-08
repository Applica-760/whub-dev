"""`whub backlog`コマンドのCLI振る舞いテスト。

検証するケース:
1. localリソースの既存backlog.mdにメモ追記
2. backlog.md未存在で新規作成+追記
3. remoteリソースへSSH mock経由で追記
4. workspace-hubへの追記
5. メモ空 → エラー
6. remote root確認失敗 → エラー
7. remote state取得失敗 → エラー
8. remote書き込み失敗 → エラー

検証しないケース:
- 実際のSSH実行
- マーカー不正パターン（_insert_memoの防御は薄いglue）
"""
from __future__ import annotations

from subprocess import CalledProcessError, CompletedProcess
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.backlog import backlog, _MARKERS
from whub.models import Manifest, SymlinkResource
from whub.tests.helpers import manifest, manifest_data
from whub.utils.managed_block import format_block


class TestBacklogSpec:
    def test_local_appends_to_existing(self, tmp_path):
        # ケース1
        m = manifest()
        local = m.resolve_project("local")
        local.resource = SymlinkResource(
            type="symlink",
            workspace_path="projects/local",
            source=str(tmp_path / "src"),
        )
        local.resource._resolved_workspace_path = tmp_path / "projects" / "local"
        (tmp_path / "src" / "docs").mkdir(parents=True)
        backlog_file = tmp_path / "src" / "docs" / "backlog.md"
        backlog_file.write_text(format_block(_MARKERS, ""))

        with patch("whub.commands.backlog.get_manifest", return_value=m):
            result = CliRunner().invoke(
                backlog, ["add feature X", "local"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "backlog" in result.output
        content = backlog_file.read_text()
        assert "- add feature X" in content

    def test_local_creates_new_backlog(self, tmp_path):
        # ケース2
        m = manifest()
        local = m.resolve_project("local")
        local.resource = SymlinkResource(
            type="symlink",
            workspace_path="projects/local",
            source=str(tmp_path / "src"),
        )
        local.resource._resolved_workspace_path = tmp_path / "projects" / "local"
        (tmp_path / "src").mkdir(parents=True)

        with patch("whub.commands.backlog.get_manifest", return_value=m):
            result = CliRunner().invoke(
                backlog, ["first memo", "local"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        content = (tmp_path / "src" / "docs" / "backlog.md").read_text()
        assert _MARKERS[0] in content
        assert "- first memo" in content

    def test_remote_appends_via_ssh(self):
        # ケース3
        m = manifest()

        def ssh_side_effect(host, cmd, **kwargs):
            if "test -d" in cmd:
                return CompletedProcess([], 0)
            if "test -f" in cmd:
                return CompletedProcess([], 0, stdout="file")
            if "cat >" not in cmd:
                return CompletedProcess([], 0, stdout=format_block(_MARKERS, ""))
            return CompletedProcess([], 0)

        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch("whub.commands.backlog.run_ssh_command", side_effect=ssh_side_effect),
        ):
            result = CliRunner().invoke(
                backlog, ["remote memo", "remote"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "backlog" in result.output

    def test_workspace_hub_appends(self, tmp_path):
        # ケース4
        data = manifest_data()
        data["projects"].append({"name": "workspace-hub"})
        m = Manifest.model_validate(data)

        ws_root = tmp_path / "ws"
        (ws_root / "docs").mkdir(parents=True)
        (ws_root / "docs" / "backlog.md").write_text(format_block(_MARKERS, ""))

        def fake_ws_resource():
            r = SymlinkResource(
                type="symlink", workspace_path=".", source=str(ws_root),
            )
            r._resolved_workspace_path = ws_root
            return r

        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch("whub.commands.backlog.workspace_hub_resource", fake_ws_resource),
        ):
            result = CliRunner().invoke(
                backlog, ["ws memo", "workspace-hub"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        content = (ws_root / "docs" / "backlog.md").read_text()
        assert "- ws memo" in content

    def test_empty_memo_errors(self):
        # ケース5
        m = manifest()
        with patch("whub.commands.backlog.get_manifest", return_value=m):
            result = CliRunner().invoke(backlog, ["", "local"])

        assert result.exit_code != 0

    def test_remote_root_check_failure_errors(self):
        # ケース6
        m = manifest()
        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch(
                "whub.commands.backlog.run_ssh_command",
                return_value=CompletedProcess([], 255, stderr="ssh failed"),
            ),
        ):
            result = CliRunner().invoke(backlog, ["memo", "remote"])

        assert result.exit_code != 0
        assert "remote backlog failed: ssh failed" in result.output

    def test_remote_state_failure_errors(self):
        # ケース7
        m = manifest()

        def ssh_side_effect(host, cmd, **kwargs):
            if "test -d" in cmd:
                return CompletedProcess([], 0)
            raise CalledProcessError(1, [], stderr="state failed")

        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch("whub.commands.backlog.run_ssh_command", side_effect=ssh_side_effect),
        ):
            result = CliRunner().invoke(backlog, ["memo", "remote"])

        assert result.exit_code != 0
        assert "remote backlog failed: state failed" in result.output

    def test_remote_write_failure_errors(self):
        # ケース8
        m = manifest()

        def ssh_side_effect(host, cmd, **kwargs):
            if "test -d" in cmd:
                return CompletedProcess([], 0)
            if "test -f" in cmd:
                return CompletedProcess([], 0, stdout="missing")
            raise CalledProcessError(1, [], stderr="write failed")

        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch("whub.commands.backlog.run_ssh_command", side_effect=ssh_side_effect),
        ):
            result = CliRunner().invoke(backlog, ["memo", "remote"])

        assert result.exit_code != 0
        assert "remote backlog failed: write failed" in result.output
