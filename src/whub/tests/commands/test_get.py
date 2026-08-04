"""`whub get`コマンドのCLI振る舞いテスト。

検証するケース:
1. workspace相対パスからscp実行、remote_files/へ保存
2. localリソース → エラー（require_resource_type）
3. リソース直下パス（rel空） → エラー
4. scp失敗時、exit codeを握りつぶさず伝搬する
5. ref形式(<project>:<path>)からもscp実行できる
6. 成功時、remote_filesメタデータへref・sha256・fetched_atを記録する

検証しないケース:
- 実際のscp実行
"""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.remote.transfer import get
from whub.core.remote_files_meta import load_remote_files_meta
from whub.tests.helpers import manifest


def _run_get(tmp_path, path: str, returncode: int = 0):
    m = manifest()
    remote_files = tmp_path / "remote_files"

    def side_effect(command, **_kwargs):
        dest = Path(command[-1])
        if returncode == 0:
            dest.write_bytes(b"remote content")
        return CompletedProcess(command, returncode)

    mock_run = MagicMock(side_effect=side_effect)
    context = MagicMock(remote_files_dir=remote_files)
    with (
        patch("whub.commands.remote.transfer.get_manifest", return_value=m),
        patch("whub.commands.remote.transfer.current_context", return_value=context),
        patch("whub.services.remote.transfer.subprocess.run", mock_run),
    ):
        result = CliRunner().invoke(get, [path], catch_exceptions=False)
    return result, mock_run, remote_files


class TestGetSpec:
    def test_gets_remote_file(self, tmp_path):
        # ケース1
        result, mock_run, _remote_files = _run_get(
            tmp_path, "projects/remote/data/file.csv"
        )

        assert result.exit_code == 0
        assert "get" in result.output
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "scp"
        # mount_rootと合成した絶対pathへresource内相対パスを繋ぐ
        assert any("/srv/remote/data/file.csv" in arg for arg in cmd)

    def test_local_resource_errors(self):
        # ケース2
        m = manifest()
        with patch("whub.commands.remote.transfer.get_manifest", return_value=m):
            result = CliRunner().invoke(get, ["projects/local/file.txt"])

        assert result.exit_code == 1
        assert "not a remote resource" in result.output

    def test_resource_root_path_errors(self):
        # ケース3
        m = manifest()
        with patch("whub.commands.remote.transfer.get_manifest", return_value=m):
            result = CliRunner().invoke(get, ["projects/remote"])

        assert result.exit_code != 0
        assert "must point to a file" in result.output

    def test_scp_exit_code_propagation(self, tmp_path):
        # ケース4
        result, _mock_run, _remote_files = _run_get(
            tmp_path, "projects/remote/data/file.csv", returncode=23
        )

        assert result.exit_code == 23

    def test_gets_remote_file_by_ref(self, tmp_path):
        # ケース5
        result, mock_run, _downloads = _run_get(tmp_path, "remote:data/file.csv")

        assert result.exit_code == 0
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "scp"

    def test_records_remote_file_metadata_on_success(self, tmp_path):
        # ケース6
        result, _mock_run, remote_files = _run_get(
            tmp_path, "projects/remote/data/file.csv"
        )

        assert result.exit_code == 0
        records = load_remote_files_meta(remote_files)
        record = records["file.csv"]
        assert record.ref == "remote:data/file.csv"
        assert (
            record.sha256 == __import__("hashlib").sha256(b"remote content").hexdigest()
        )
