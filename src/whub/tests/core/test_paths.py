"""`whub.core.paths`の仕様テスト。

検証するケース:
1. `WHUB_DATA_DIR`環境変数があれば、`.whub/config.toml`より優先する。
2. `WHUB_DATA_DIR`がなければ、`WHUB_ROOT/.whub/config.toml`の`data_dir`を使う。
3. `manifest.yaml`/`todos.yaml`/`downloads`は`data_dir`配下へ解決する。
4. config欠落・TOML不正・`data_dir`欠落は`PathError`にする。
5. 新resolverは開始directoryから親方向へ最寄りの`.whub/config.toml`を探す。
6. 新resolverはcontextが見つからなければ`PathError`にする。
7. 新resolverはpackage位置を使う旧`whub_root`と並存する。

検証しないケース:
1. 環境変数なしでパッケージ位置からworkspace rootを推定する挙動。
"""

from __future__ import annotations
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from whub.core.paths import (
    PathError,
    downloads_dir,
    find_context_root,
    manifest_path,
    todo_path,
    whub_data_dir,
    whub_root,
)
from whub.tests.helpers import write_config


class TestPathsSpec:
    def test_context_root_finds_current_or_ancestor_config(self, tmp_path) -> None:
        root = tmp_path / "context"
        nested = root / "nested" / "child"
        nested.mkdir(parents=True)
        config_dir = root / ".whub"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text("")

        assert find_context_root(root) == root.resolve()
        assert find_context_root(nested) == root.resolve()

    def test_context_root_uses_nearest_config(self, tmp_path) -> None:
        outer = tmp_path / "outer"
        inner = outer / "inner"
        nested = inner / "nested"
        nested.mkdir(parents=True)
        for root in (outer, inner):
            config_dir = root / ".whub"
            config_dir.mkdir()
            (config_dir / "config.toml").write_text("")

        assert find_context_root(nested) == inner.resolve()

    def test_context_root_reports_missing_config(self, tmp_path) -> None:
        with pytest.raises(PathError, match="whub context not found"):
            find_context_root(tmp_path)

    def test_context_root_is_independent_from_legacy_package_root(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        config_dir = tmp_path / ".whub"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text("")
        monkeypatch.delenv("WHUB_ROOT", raising=False)

        assert find_context_root(tmp_path) == tmp_path.resolve()
        assert whub_root() != tmp_path.resolve()

    def test_environment_data_dir_overrides_config(self) -> None:
        with (
            tempfile.TemporaryDirectory() as root,
            tempfile.TemporaryDirectory() as data,
        ):
            # ケース1,3
            with patch.dict(
                os.environ,
                {"WHUB_ROOT": root, "WHUB_DATA_DIR": data},
                clear=True,
            ):
                expected = Path(data).resolve()
                assert whub_data_dir() == expected
                assert manifest_path() == expected / "manifest.yaml"
                assert todo_path() == expected / "todos.yaml"
                assert downloads_dir() == expected / "downloads"

    def test_config_data_dir_is_used_without_environment_override(self) -> None:
        with (
            tempfile.TemporaryDirectory() as root,
            tempfile.TemporaryDirectory() as data,
        ):
            # ケース2
            write_config(Path(root), Path(data))
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                assert whub_data_dir() == Path(data).resolve()

    def test_missing_or_invalid_config_is_path_error(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            # ケース4
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                with pytest.raises(PathError, match="data_dir is not configured"):
                    whub_data_dir()

            # ケース4
            config_dir = Path(root) / ".whub"
            config_dir.mkdir()
            (config_dir / "config.toml").write_text("data_dir = [")
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                with pytest.raises(PathError, match="invalid whub config"):
                    whub_data_dir()

            # ケース4
            (config_dir / "config.toml").write_text("other = 'value'\n")
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                with pytest.raises(PathError, match="missing data_dir"):
                    whub_data_dir()
