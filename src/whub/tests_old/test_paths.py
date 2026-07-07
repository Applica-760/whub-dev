from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import click

from whub.paths import manifest_path, whub_data_dir


class PathsTest(unittest.TestCase):
    def test_data_dir_env_wins(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as data:
            with patch.dict(
                os.environ,
                {"WHUB_ROOT": root, "WHUB_DATA_DIR": data},
                clear=True,
            ):
                self.assertEqual(whub_data_dir(), Path(data).resolve())
                self.assertEqual(manifest_path(), Path(data).resolve() / "manifest.yaml")

    def test_data_dir_reads_config(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as data:
            config_dir = Path(root) / ".whub"
            config_dir.mkdir()
            (config_dir / "config.toml").write_text(f'data_dir = "{data}"\n')

            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                self.assertEqual(whub_data_dir(), Path(data).resolve())

    def test_data_dir_requires_config(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                with self.assertRaises(click.ClickException):
                    whub_data_dir()


if __name__ == "__main__":
    unittest.main()
