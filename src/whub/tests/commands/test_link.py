"""`whub link`コマンドのCLI振る舞いテスト。

検証するケース:
1. health=missingでシンボリックリンク作成、"link"出力
2. health=okで"skip"出力
3. RemoteResourceはスキップされる
4. symlink作成失敗時にWARN出力
5. .gitignoreにwhub runtime metadataだけがマーカー付きで追記される

検証しないケース:
- 実ファイルシステム上のsymlink作成（inspect_symlinkのmockで境界を閉じる）
- 利用者がmarkerなしで管理する.gitignore entryの意味
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.link import _GITIGNORE_ENTRIES, _GITIGNORE_MARKERS, link
from whub.core.health import ResourceHealth
from whub.tests.helpers import manifest


def _invoke_link(m, health_side_effect, *, symlink_to_side_effect=None, cwd=None):
    """linkコマンドを共通mock付きで実行する。"""
    with (
        patch("whub.commands.link.get_manifest", return_value=m),
        patch("whub.commands.link.inspect_symlink", side_effect=health_side_effect),
        patch.object(Path, "symlink_to", side_effect=symlink_to_side_effect),
        patch.object(Path, "cwd", return_value=cwd or Path("/tmp/test-cwd")),
        patch(
            "whub.commands.link.current_context",
            return_value=SimpleNamespace(workspace_root=cwd or Path("/tmp/test-cwd")),
        ),
    ):
        return CliRunner().invoke(link, catch_exceptions=False)


class TestLinkSpec:
    def test_creates_symlink_when_missing(self, tmp_path):
        # ケース1
        m = manifest()
        health_seq = [
            ResourceHealth("missing"),
            ResourceHealth("ok"),
        ]
        with (
            patch("whub.commands.link.get_manifest", return_value=m),
            patch("whub.commands.link.inspect_symlink", side_effect=health_seq),
            patch.object(Path, "symlink_to"),
            patch.object(Path, "cwd", return_value=tmp_path),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            result = CliRunner().invoke(link, catch_exceptions=False)

        assert result.exit_code == 0
        assert "link" in result.output
        assert "1 created" in result.output

    def test_skips_when_ok(self, tmp_path):
        # ケース2
        m = manifest()
        with (
            patch("whub.commands.link.get_manifest", return_value=m),
            patch(
                "whub.commands.link.inspect_symlink", return_value=ResourceHealth("ok")
            ),
            patch.object(Path, "cwd", return_value=tmp_path),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            result = CliRunner().invoke(link, catch_exceptions=False)

        assert result.exit_code == 0
        assert "skip" in result.output
        assert "1 skipped" in result.output

    def test_ignores_non_symlink_resources(self, tmp_path):
        # ケース3
        m = manifest()
        with (
            patch("whub.commands.link.get_manifest", return_value=m),
            patch(
                "whub.commands.link.inspect_symlink", return_value=ResourceHealth("ok")
            ),
            patch.object(Path, "cwd", return_value=tmp_path),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            result = CliRunner().invoke(link, catch_exceptions=False)

        assert "remote" not in result.output.lower().split("done")[0]

    def test_warns_on_symlink_failure(self, tmp_path):
        # ケース4
        m = manifest()
        with (
            patch("whub.commands.link.get_manifest", return_value=m),
            patch(
                "whub.commands.link.inspect_symlink",
                return_value=ResourceHealth("missing"),
            ),
            patch.object(Path, "symlink_to", side_effect=OSError("permission denied")),
            patch.object(Path, "cwd", return_value=tmp_path),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            result = CliRunner().invoke(link, catch_exceptions=False)

        assert "WARN" in result.output
        assert "1 warnings" in result.output

    def test_updates_gitignore(self, tmp_path):
        # ケース5
        m = manifest()
        with (
            patch("whub.commands.link.get_manifest", return_value=m),
            patch(
                "whub.commands.link.inspect_symlink", return_value=ResourceHealth("ok")
            ),
            patch.object(Path, "cwd", return_value=tmp_path),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            CliRunner().invoke(link, catch_exceptions=False)

        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert _GITIGNORE_MARKERS[0] in content
        assert _GITIGNORE_MARKERS[1] in content
        for entry in _GITIGNORE_ENTRIES:
            assert entry in content
        assert "/projects" in content
        for entry in ("AGENTS.md", ".agents/"):
            assert entry not in content

    def test_replaces_managed_block_with_runtime_metadata_only(self, tmp_path):
        (tmp_path / ".gitignore").write_text(
            "# user entry\n"
            "# whub link (auto-generated): start\n"
            "projects\nAGENTS.md\n.agents/\n.claude/\n"
            "# whub link (auto-generated): end\n"
        )
        m = manifest()
        with (
            patch("whub.commands.link.get_manifest", return_value=m),
            patch(
                "whub.commands.link.inspect_symlink", return_value=ResourceHealth("ok")
            ),
            patch.object(Path, "cwd", return_value=tmp_path),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            CliRunner().invoke(link, catch_exceptions=False)

        content = (tmp_path / ".gitignore").read_text()
        assert "# user entry" in content
        for entry in _GITIGNORE_ENTRIES:
            assert entry in content
        assert "/projects" in content
        for entry in ("AGENTS.md", ".agents/", ".claude/"):
            assert entry not in content

    def test_updates_legacy_gitignore_without_dropping_next_line(self, tmp_path):
        # ケース6
        (tmp_path / ".gitignore").write_text(
            "# whub link (auto-generated)\nprojects\n.keep\n"
        )
        m = manifest()
        with (
            patch("whub.commands.link.get_manifest", return_value=m),
            patch(
                "whub.commands.link.inspect_symlink", return_value=ResourceHealth("ok")
            ),
            patch.object(Path, "cwd", return_value=tmp_path),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            CliRunner().invoke(link, catch_exceptions=False)

        content = (tmp_path / ".gitignore").read_text()
        assert _GITIGNORE_MARKERS[0] in content
        assert _GITIGNORE_MARKERS[1] in content
        assert ".keep" in content
        assert "/projects" in content

    def test_errors_outside_workspace_hub_root(self, tmp_path):
        # ケース7
        with (
            patch.object(Path, "cwd", return_value=tmp_path / "other"),
            patch(
                "whub.commands.link.current_context",
                return_value=SimpleNamespace(workspace_root=tmp_path),
            ),
        ):
            result = CliRunner().invoke(link)

        assert result.exit_code != 0
        assert "workspace root" in result.output
