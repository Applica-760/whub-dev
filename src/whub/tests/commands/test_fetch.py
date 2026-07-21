"""`whub fetch`コマンドのCLI振る舞いテスト。

検証するケース:
1. workspace相対パスからscp実行、downloads/へ保存
2. localリソース → エラー（require_resource_type）
3. リソース直下パス（rel空） → エラー
4. scp失敗時、exit codeを握りつぶさず伝搬する

検証しないケース:
- 実際のscp実行
"""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.fetch import fetch
from whub.tests.helpers import manifest


class TestFetchSpec:
    def test_fetches_remote_file(self, tmp_path):
        # ケース1
        m = manifest()
        downloads = tmp_path / "downloads"
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.commands.fetch.get_manifest", return_value=m),
            patch("whub.commands.fetch.downloads_dir", return_value=downloads),
            patch("whub.commands.fetch.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(
                fetch,
                ["projects/remote/data/file.csv"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "fetch" in result.output
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "scp"

    def test_local_resource_errors(self):
        # ケース2
        m = manifest()
        with patch("whub.commands.fetch.get_manifest", return_value=m):
            result = CliRunner().invoke(fetch, ["projects/local/file.txt"])

        assert result.exit_code == 1
        assert "not a remote resource" in result.output

    def test_resource_root_path_errors(self):
        # ケース3
        m = manifest()
        with patch("whub.commands.fetch.get_manifest", return_value=m):
            result = CliRunner().invoke(fetch, ["projects/remote"])

        assert result.exit_code != 0
        assert "must point to a file" in result.output

    def test_scp_exit_code_propagation(self, tmp_path):
        # ケース4
        m = manifest()
        downloads = tmp_path / "downloads"
        mock_run = MagicMock(return_value=CompletedProcess([], 23))
        with (
            patch("whub.commands.fetch.get_manifest", return_value=m),
            patch("whub.commands.fetch.downloads_dir", return_value=downloads),
            patch("whub.commands.fetch.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(fetch, ["projects/remote/data/file.csv"])

        assert result.exit_code == 23
