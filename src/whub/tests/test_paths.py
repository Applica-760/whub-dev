"""`whub.paths`の仕様テスト。

検証するケース:
1. `WHUB_DATA_DIR`環境変数があれば、`.whub/config.toml`より優先する。
2. `WHUB_DATA_DIR`がなければ、`WHUB_ROOT/.whub/config.toml`の`data_dir`を使う。
3. `manifest.yaml`/`todos.yaml`/`downloads`は`data_dir`配下へ解決する。
4. config欠落・TOML不正・`data_dir`欠落は`ClickException`にする。

検証しないケース:
1. 環境変数なしでパッケージ位置からworkspace rootを推定する挙動。
"""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import click
from whub.paths import downloads_dir, manifest_path, todo_path, whub_data_dir
from whub.tests.helpers import write_config


class PathsSpecTest(unittest.TestCase):
    def test_environment_data_dir_overrides_config(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as data:
            # ケース1,3
            with patch.dict(
                os.environ,
                {"WHUB_ROOT": root, "WHUB_DATA_DIR": data},
                clear=True,
            ):
                expected = Path(data).resolve()
                self.assertEqual(whub_data_dir(), expected)
                self.assertEqual(manifest_path(), expected / "manifest.yaml")
                self.assertEqual(todo_path(), expected / "todos.yaml")
                self.assertEqual(downloads_dir(), expected / "downloads")

    def test_config_data_dir_is_used_without_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as data:
            # ケース2
            write_config(Path(root), Path(data))
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                self.assertEqual(whub_data_dir(), Path(data).resolve())

    def test_missing_or_invalid_config_is_click_error(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            # ケース4
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                with self.assertRaisesRegex(click.ClickException, "data_dir is not configured"):
                    whub_data_dir()

            # ケース4
            config_dir = Path(root) / ".whub"
            config_dir.mkdir()
            (config_dir / "config.toml").write_text("data_dir = [")
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                with self.assertRaisesRegex(click.ClickException, "invalid whub config"):
                    whub_data_dir()

            # ケース4
            (config_dir / "config.toml").write_text("other = 'value'\n")
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                with self.assertRaisesRegex(click.ClickException, "missing data_dir"):
                    whub_data_dir()


if __name__ == "__main__":
    unittest.main()
