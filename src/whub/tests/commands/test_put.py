"""`whub put`コマンドのCLI振る舞いテスト。

検証するケース:
1. fetchメタのあるファイルをputし、remoteへアトミック書き込み+メタ更新
2. downloads内にファイルがない場合はエラー
3. fetchメタがないファイルはエラー
4. remote hashがbaseline hashと一致しない場合はlost updateエラー
5. remote hashの取得に失敗した場合はエラー
6. remote書き込みが失敗した場合はエラー

検証しないケース:
- 実際のSSH/SCP実行
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.put import put
from whub.core.download_meta import load_download_meta, record_download
from whub.tests.helpers import manifest


def _setup_downloads(tmp_path: Path, content: str = "edited content") -> Path:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    local = downloads / "file.csv"
    local.write_text(content)
    original_hash = hashlib.sha256(b"remote content").hexdigest()
    record_download(downloads, "file.csv", "remote:data/file.csv", original_hash, "2026-01-01T00:00:00+00:00")
    return downloads


def _run_put(
    tmp_path: Path,
    local_name: str = "file.csv",
    remote_hash: str | None = None,
    write_returncode: int = 0,
    write_stderr: str = "",
    setup: bool = True,
) -> tuple:
    m = manifest()
    if setup:
        downloads = _setup_downloads(tmp_path)
    else:
        downloads = tmp_path / "downloads"

    if remote_hash is None:
        remote_hash = hashlib.sha256(b"remote content").hexdigest()

    context = MagicMock(downloads_dir=downloads)
    with (
        patch("whub.commands.put.get_manifest", return_value=m),
        patch("whub.commands.put.current_context", return_value=context),
        patch("whub.commands.put.remote_file_hash", return_value=remote_hash),
        patch(
            "whub.commands.put.remote_write_file",
            return_value=CompletedProcess([], write_returncode, "", write_stderr),
        ) as mock_write,
    ):
        result = CliRunner().invoke(put, [local_name], catch_exceptions=False)
    return result, mock_write, downloads


class TestPutSpec:
    def test_puts_fetched_file(self, tmp_path: Path) -> None:
        # ケース1
        result, mock_write, downloads = _run_put(tmp_path)

        assert result.exit_code == 0
        assert "put" in result.output
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert "data/file.csv" in call_args[0][1]
        assert call_args[0][2] == "edited content"
        records = load_download_meta(downloads)
        assert records["file.csv"].sha256 == hashlib.sha256(b"edited content").hexdigest()

    def test_file_not_in_downloads_errors(self, tmp_path: Path) -> None:
        # ケース2
        downloads = tmp_path / "downloads"
        downloads.mkdir()
        context = MagicMock(downloads_dir=downloads)
        with patch("whub.commands.put.current_context", return_value=context):
            result = CliRunner().invoke(put, ["nonexistent.csv"])

        assert result.exit_code != 0
        assert "file not found" in result.output

    def test_no_fetch_metadata_errors(self, tmp_path: Path) -> None:
        # ケース3
        downloads = tmp_path / "downloads"
        downloads.mkdir()
        (downloads / "orphan.csv").write_text("data")
        context = MagicMock(downloads_dir=downloads)
        with patch("whub.commands.put.current_context", return_value=context):
            result = CliRunner().invoke(put, ["orphan.csv"])

        assert result.exit_code != 0
        assert "no fetch metadata" in result.output

    def test_lost_update_detection(self, tmp_path: Path) -> None:
        # ケース4
        result, _mock_write, _downloads = _run_put(
            tmp_path, remote_hash="different_hash"
        )

        assert result.exit_code != 0
        assert "changed or is unreadable" in result.output

    def test_remote_hash_failure_errors(self, tmp_path: Path) -> None:
        # ケース5
        m = manifest()
        downloads = _setup_downloads(tmp_path)
        context = MagicMock(downloads_dir=downloads)
        with (
            patch("whub.commands.put.get_manifest", return_value=m),
            patch("whub.commands.put.current_context", return_value=context),
            patch("whub.commands.put.remote_file_hash", return_value=None),
        ):
            result = CliRunner().invoke(put, ["file.csv"], catch_exceptions=False)

        assert result.exit_code != 0
        assert "changed or is unreadable" in result.output

    def test_remote_write_failure_errors(self, tmp_path: Path) -> None:
        # ケース6
        result, _mock_write, _downloads = _run_put(
            tmp_path, write_returncode=1, write_stderr="permission denied"
        )

        assert result.exit_code != 0
        assert "remote write failed" in result.output
