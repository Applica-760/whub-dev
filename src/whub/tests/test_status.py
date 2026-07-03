from __future__ import annotations

import importlib
import subprocess
import unittest
from unittest.mock import patch

from whub.health import ResourceHealth
from whub.models import Manifest


status_module = importlib.import_module("whub.commands.status")


class StatusTest(unittest.TestCase):
    def _remote_project(self):
        manifest = Manifest.model_validate({
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
                        "git": {"url": "git@example.com:repo.git"},
                    },
                },
            ],
        })
        return manifest.projects[0]

    def test_remote_git_failure_does_not_override_health(self) -> None:
        project = self._remote_project()

        with (
            patch.object(
                status_module,
                "inspect_remote",
                return_value=ResourceHealth("ok"),
            ),
            patch.object(
                status_module,
                "run_ssh_command",
                return_value=subprocess.CompletedProcess([], 1, "", "fatal"),
            ),
        ):
            info = status_module._fetch_remote_info(project.resource, project)

        self.assertEqual(info.health.state, "ok")
        self.assertEqual(info.git_diff, "-")


if __name__ == "__main__":
    unittest.main()
