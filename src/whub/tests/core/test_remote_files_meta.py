"""`whub.core.remote_files_meta`の仕様テスト。

検証するケース:
1. メタファイル未存在時、`load_remote_files_meta()`は空dictを返す。
2. `record_remote_file()`で書いた内容を`load_remote_files_meta()`で読み戻せる。
3. `get_remote_file_record()`は既存名の記録を返し、未知名はNoneを返す。
4. `resolve_remote_file_name()`は同一refの既存fileと同名を返す。
5. `resolve_remote_file_name()`は新規refでbasenameが空いていればそのまま返す。
6. `resolve_remote_file_name()`はbasenameが記録済みまたは実ファイルと衝突する場合、連番を振る。
7. `update_remote_file_hash()`はrefを保持したままsha256とfetched_atを更新する。
8. `remove_remote_file_record()`はrecordを消し、最後のrecordならメタJSONも消す。

検証しないケース:
1. メタファイルの同時書き込み競合。
"""

from __future__ import annotations

from pathlib import Path

from whub.core.remote_files_meta import (
    get_remote_file_record,
    load_remote_files_meta,
    meta_path,
    record_remote_file,
    remove_remote_file_record,
    resolve_remote_file_name,
    update_remote_file_hash,
)


class TestDownloadMetaSpec:
    def test_load_returns_empty_when_meta_file_missing(self, tmp_path: Path) -> None:
        # ケース1
        assert load_remote_files_meta(tmp_path) == {}

    def test_record_download_round_trips(self, tmp_path: Path) -> None:
        # ケース2
        record_remote_file(
            tmp_path,
            "issue.md",
            "la-il:docs/issue.md",
            "a" * 64,
            "2026-07-24T00:00:00Z",
        )

        records = load_remote_files_meta(tmp_path)

        assert records["issue.md"].ref == "la-il:docs/issue.md"
        assert records["issue.md"].sha256 == "a" * 64
        assert records["issue.md"].fetched_at == "2026-07-24T00:00:00Z"

    def test_get_download_record_returns_record_or_none(self, tmp_path: Path) -> None:
        # ケース3
        record_remote_file(
            tmp_path,
            "issue.md",
            "la-il:docs/issue.md",
            "a" * 64,
            "2026-07-24T00:00:00Z",
        )

        assert get_remote_file_record(tmp_path, "issue.md") is not None
        assert get_remote_file_record(tmp_path, "missing.md") is None

    def test_resolve_local_name_reuses_name_for_same_ref(self, tmp_path: Path) -> None:
        # ケース4
        record_remote_file(
            tmp_path,
            "issue.md",
            "la-il:docs/issue.md",
            "a" * 64,
            "2026-07-24T00:00:00Z",
        )

        assert (
            resolve_remote_file_name(tmp_path, "la-il:docs/issue.md", "issue.md")
            == "issue.md"
        )

    def test_resolve_local_name_returns_preferred_name_when_free(
        self, tmp_path: Path
    ) -> None:
        # ケース5
        assert (
            resolve_remote_file_name(tmp_path, "la-il:docs/new.md", "new.md")
            == "new.md"
        )

    def test_resolve_local_name_appends_index_on_collision(
        self, tmp_path: Path
    ) -> None:
        # ケース6
        record_remote_file(
            tmp_path,
            "issue.md",
            "la-il:docs/a/issue.md",
            "a" * 64,
            "2026-07-24T00:00:00Z",
        )

        assert (
            resolve_remote_file_name(tmp_path, "esn-lab:docs/b/issue.md", "issue.md")
            == "issue-2.md"
        )

        (tmp_path / "issue-2.md").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "issue-2.md").write_text("existing file not tracked in meta")

        assert (
            resolve_remote_file_name(tmp_path, "esn-lab:docs/c/issue.md", "issue.md")
            == "issue-3.md"
        )

    def test_update_download_hash_keeps_ref_and_replaces_hash(
        self, tmp_path: Path
    ) -> None:
        # ケース7
        record_remote_file(
            tmp_path,
            "issue.md",
            "la-il:docs/issue.md",
            "a" * 64,
            "2026-07-24T00:00:00Z",
        )

        update_remote_file_hash(
            tmp_path, "issue.md", "b" * 64, "2026-07-24T01:00:00Z"
        )

        record = get_remote_file_record(tmp_path, "issue.md")
        assert record is not None
        assert record.ref == "la-il:docs/issue.md"
        assert record.sha256 == "b" * 64
        assert record.fetched_at == "2026-07-24T01:00:00Z"

    def test_remove_record_removes_metadata_file_when_empty(self, tmp_path: Path) -> None:
        # ケース8
        record_remote_file(
            tmp_path,
            "issue.md",
            "la-il:docs/issue.md",
            "a" * 64,
            "2026-07-24T00:00:00Z",
        )

        remove_remote_file_record(tmp_path, "issue.md")

        assert not meta_path(tmp_path).exists()
