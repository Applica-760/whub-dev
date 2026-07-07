"""`whub roadmap`コマンドのCLI振る舞いテスト。

検証するケース:
1. localリソースの既存roadmap.mdにメモ追記
2. roadmap.md未存在で新規作成+追記
3. remoteリソースへSSH mock経由で追記
4. workspace-hubへの追記
5. メモ空 → エラー

検証しないケース:
- 実際のSSH実行
- マーカー不正パターン（_insert_memoの防御は薄いglue）
"""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from whub.commands.roadmap import roadmap, _MARKER_START, _MARKER_END
from whub.models import Manifest, Project, SymlinkResource
from whub.tests.helpers import manifest, manifest_data


def _seed(name: str) -> str:
    return f"# {name} Roadmap\n\n{_MARKER_START}\n{_MARKER_END}\n"


class TestRoadmapSpec:
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
        roadmap_file = tmp_path / "src" / "docs" / "roadmap.md"
        roadmap_file.write_text(_seed("local"))

        with patch("whub.commands.roadmap.get_manifest", return_value=m):
            result = CliRunner().invoke(
                roadmap, ["local", "add", "feature", "X"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "roadmap" in result.output
        content = roadmap_file.read_text()
        assert "- add feature X" in content

    def test_local_creates_new_roadmap(self, tmp_path):
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

        with patch("whub.commands.roadmap.get_manifest", return_value=m):
            result = CliRunner().invoke(
                roadmap, ["local", "first", "memo"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        content = (tmp_path / "src" / "docs" / "roadmap.md").read_text()
        assert _MARKER_START in content
        assert "- first memo" in content

    def test_remote_appends_via_ssh(self):
        # ケース3
        m = manifest()
        mock_ssh = MagicMock()
        mock_ssh.return_value = CompletedProcess([], 0, stdout="file", stderr="")
        mock_ssh.return_value.stdout = "file"

        def ssh_side_effect(host, cmd, **kwargs):
            if "test -d" in cmd:
                return CompletedProcess([], 0)
            if "test -f" in cmd:
                return CompletedProcess([], 0, stdout="file")
            if "cat >" not in cmd:
                return CompletedProcess([], 0, stdout=_seed("remote"))
            return CompletedProcess([], 0)

        with (
            patch("whub.commands.roadmap.get_manifest", return_value=m),
            patch("whub.commands.roadmap.run_ssh_command", side_effect=ssh_side_effect),
        ):
            result = CliRunner().invoke(
                roadmap, ["remote", "remote", "memo"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "roadmap" in result.output

    def test_workspace_hub_appends(self, tmp_path):
        # ケース4
        data = manifest_data()
        data["projects"].append({"name": "workspace-hub"})
        m = Manifest.model_validate(data)

        ws_root = tmp_path / "ws"
        (ws_root / "docs").mkdir(parents=True)
        (ws_root / "docs" / "roadmap.md").write_text(_seed("workspace-hub"))

        def fake_ws_resource():
            r = SymlinkResource(
                type="symlink", workspace_path=".", source=str(ws_root),
            )
            r._resolved_workspace_path = ws_root
            return r

        with (
            patch("whub.commands.roadmap.get_manifest", return_value=m),
            patch("whub.commands.roadmap.workspace_hub_resource", fake_ws_resource),
        ):
            result = CliRunner().invoke(
                roadmap, ["workspace-hub", "ws", "memo"], catch_exceptions=False,
            )

        assert result.exit_code == 0
        content = (ws_root / "docs" / "roadmap.md").read_text()
        assert "- ws memo" in content

    def test_empty_memo_errors(self):
        # ケース5
        m = manifest()
        with patch("whub.commands.roadmap.get_manifest", return_value=m):
            result = CliRunner().invoke(roadmap, ["local"])

        assert result.exit_code != 0
