from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.init import init


class InitCommandTest(unittest.TestCase):
    def test_writes_data_dir_config(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as data:
            data_dir = Path(data)
            data_dir.joinpath("manifest.yaml").write_text("version: '2'\n")

            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                result = CliRunner().invoke(init, [str(data_dir)])

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(
                (Path(root) / ".whub" / "config.toml").read_text(),
                f'data_dir = "{data_dir.resolve()}"\n',
            )

    def test_rejects_existing_symlink_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as data:
            data_dir = Path(data)
            data_dir.joinpath("manifest.yaml").write_text("version: '2'\n")
            symlink = Path(root) / ".whub"
            symlink.symlink_to(data_dir, target_is_directory=True)

            with patch.dict(os.environ, {"WHUB_ROOT": root}, clear=True):
                result = CliRunner().invoke(init, [str(data_dir)])

            self.assertEqual(result.exit_code, 1)
            self.assertIn("is a symlink", result.output)


if __name__ == "__main__":
    unittest.main()
