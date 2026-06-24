from __future__ import annotations

import importlib
import subprocess
import unittest
from unittest.mock import patch

from whub.models import Manifest


remote_module = importlib.import_module("whub.remote")


class RemoteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.host = Manifest.model_validate({
            "version": "2",
            "hosts": {
                "server": {
                    "hostname": "example.com",
                    "user": "user",
                    "port": 2222,
                    "identity_file": "/tmp/key",
                },
            },
        }).hosts["server"]

    def test_run_ssh_command_builds_and_executes_command(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "output", "")
        with patch.object(
            remote_module.subprocess,
            "run",
            return_value=completed,
        ) as execute:
            result = remote_module.run_ssh_command(
                self.host,
                "cat /srv/file",
                input="content",
                timeout=30,
                check=True,
            )

        self.assertIs(result, completed)
        execute.assert_called_once_with(
            [
                "ssh",
                "-i", "/tmp/key",
                "-p", "2222",
                "user@example.com",
                "cat /srv/file",
            ],
            input="content",
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )

    def test_run_rsync_command_builds_and_executes_command(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(
            remote_module.subprocess,
            "run",
            return_value=completed,
        ) as execute:
            result = remote_module.run_rsync_command(
                self.host,
                "/local/skills",
                "/remote/skills",
                timeout=30,
                check=True,
            )

        self.assertIs(result, completed)
        execute.assert_called_once_with(
            [
                "rsync", "-a",
                "-e", "ssh -i /tmp/key -p 2222",
                "/local/skills/",
                "user@example.com:/remote/skills/",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
