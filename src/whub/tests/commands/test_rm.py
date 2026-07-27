"""`whub remote rm` のCLI振る舞いテスト。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.remote.transfer import rm
from whub.core.remote_files_meta import (
    get_remote_file_record,
    meta_path,
    record_remote_file,
)


def _setup_remote_files(tmp_path: Path, exists: bool = True) -> Path:
    remote_files = tmp_path / "remote_files"
    remote_files.mkdir()
    if exists:
        (remote_files / "file.csv").write_text("remote content")
    record_remote_file(
        remote_files,
        "file.csv",
        "remote:data/file.csv",
        "a" * 64,
        "2026-07-27T00:00:00Z",
    )
    return remote_files


class TestRmSpec:
    def test_removes_managed_file_and_its_metadata(self, tmp_path: Path) -> None:
        remote_files = _setup_remote_files(tmp_path)
        context = MagicMock(remote_files_dir=remote_files)

        with patch("whub.commands.remote.transfer.current_context", return_value=context):
            result = CliRunner().invoke(rm, ["file.csv"])

        assert result.exit_code == 0
        assert not (remote_files / "file.csv").exists()
        assert get_remote_file_record(remote_files, "file.csv") is None
        assert not meta_path(remote_files).exists()

    def test_unmanaged_file_errors_without_deleting_it(self, tmp_path: Path) -> None:
        remote_files = tmp_path / "remote_files"
        remote_files.mkdir()
        unmanaged = remote_files / "unmanaged.csv"
        unmanaged.write_text("content")
        context = MagicMock(remote_files_dir=remote_files)

        with patch("whub.commands.remote.transfer.current_context", return_value=context):
            result = CliRunner().invoke(rm, ["unmanaged.csv"])

        assert result.exit_code != 0
        assert "no fetch metadata" in result.output
        assert unmanaged.exists()

    def test_removes_stale_metadata_when_managed_file_is_missing(
        self, tmp_path: Path
    ) -> None:
        remote_files = _setup_remote_files(tmp_path, exists=False)
        context = MagicMock(remote_files_dir=remote_files)

        with patch("whub.commands.remote.transfer.current_context", return_value=context):
            result = CliRunner().invoke(rm, ["file.csv"])

        assert result.exit_code == 0
        assert not meta_path(remote_files).exists()
