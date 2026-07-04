from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

import click

from whub.commands import roadmap as roadmap_module
from whub.models import Manifest


def _manifest() -> Manifest:
    return Manifest.model_validate({
        "version": "2",
        "hosts": {
            "server": {
                "hostname": "example.com",
                "user": "user",
                "identity_file": "/tmp/key",
            },
        },
        "projects": [
            {
                "name": "remote",
                "resource": {
                    "type": "remote",
                    "host": "server",
                    "path": "/srv/remote",
                    "workspace_path": "remote/remote",
                },
            },
        ],
    })


class RemoteRoadmapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.resource = _manifest().projects[0].resource

    def _result(
        self,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], returncode, stdout, stderr)

    def test_appends_to_existing_remote_roadmap(self) -> None:
        content = roadmap_module._seed("remote")
        with patch.object(
            roadmap_module,
            "run_ssh_command",
            side_effect=[
                self._result(),
                self._result("file\n"),
                self._result(content),
                self._result(),
            ],
        ) as execute:
            roadmap_module._remote_roadmap(self.resource, ("remote", "new memo"))

        self.assertEqual(execute.call_count, 4)
        self.assertEqual(
            execute.call_args.kwargs["input"],
            roadmap_module._insert_memo(content, "new memo"),
        )

    def test_seeds_missing_remote_roadmap(self) -> None:
        with patch.object(
            roadmap_module,
            "run_ssh_command",
            side_effect=[
                self._result(),
                self._result("missing\n"),
                self._result(),
            ],
        ) as execute:
            roadmap_module._remote_roadmap(self.resource, ("remote", "first memo"))

        self.assertEqual(execute.call_count, 3)
        self.assertEqual(
            execute.call_args.kwargs["input"],
            roadmap_module._insert_memo(
                roadmap_module._seed("remote"),
                "first memo",
            ),
        )

    def test_rejects_missing_remote_root(self) -> None:
        with patch.object(
            roadmap_module,
            "run_ssh_command",
            return_value=self._result(returncode=1),
        ) as execute:
            with self.assertRaisesRegex(
                click.ClickException,
                "remote resource path does not exist",
            ):
                roadmap_module._remote_roadmap(self.resource, ("remote", "memo"))

        self.assertEqual(execute.call_count, 1)

    def test_rejects_failed_remote_root_check(self) -> None:
        with patch.object(
            roadmap_module,
            "run_ssh_command",
            return_value=self._result(stderr="ssh failed", returncode=255),
        ) as execute:
            with self.assertRaisesRegex(
                click.ClickException,
                "remote roadmap failed: ssh failed",
            ):
                roadmap_module._remote_roadmap(self.resource, ("remote", "memo"))

        self.assertEqual(execute.call_count, 1)

    def test_rejects_invalid_existing_remote_roadmap(self) -> None:
        with patch.object(
            roadmap_module,
            "run_ssh_command",
            side_effect=[
                self._result(),
                self._result("file\n"),
                self._result("bad content\n"),
            ],
        ) as execute:
            with self.assertRaisesRegex(
                click.ClickException,
                "roadmap markers are missing or duplicated",
            ):
                roadmap_module._remote_roadmap(self.resource, ("remote", "memo"))

        self.assertEqual(execute.call_count, 3)

    def test_wraps_ssh_failure(self) -> None:
        error = subprocess.CalledProcessError(1, ["ssh"], stderr="failed")
        with patch.object(
            roadmap_module,
            "run_ssh_command",
            side_effect=error,
        ):
            with self.assertRaisesRegex(
                click.ClickException,
                "remote roadmap failed",
            ):
                roadmap_module._remote_roadmap(self.resource, ("remote", "memo"))


if __name__ == "__main__":
    unittest.main()
