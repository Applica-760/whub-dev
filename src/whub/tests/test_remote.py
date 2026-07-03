from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path
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

    def test_build_remote_exec_command_quotes_arguments(self) -> None:
        remote_command = remote_module.build_remote_exec_command(
            "/srv/my project",
            ("echo", "hello world"),
        )

        self.assertEqual(
            remote_command,
            "cd '/srv/my project' && exec echo 'hello world'",
        )

    def test_build_sshfs_command(self) -> None:
        cmd = remote_module.build_sshfs_command(
            self.host,
            "/srv/data",
            Path("/ws/remote/data"),
            volname="whub-data",
        )

        self.assertEqual(cmd, [
            "sshfs",
            "user@example.com:/srv/data",
            "/ws/remote/data",
            "-s",
            "-o", "IdentityFile=/tmp/key",
            "-o", "port=2222",
            "-o", "reconnect",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "noappledouble",
            "-o", "noapplexattr",
            "-o", "defer_permissions",
            "-o", "volname=whub-data",
        ])

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
