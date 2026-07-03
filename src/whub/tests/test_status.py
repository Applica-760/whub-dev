from __future__ import annotations

import importlib
import subprocess
import unittest
from unittest.mock import patch

from whub.health import ResourceHealth
from whub.models import Manifest


status_module = importlib.import_module("whub.commands.status")


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
                    "git": {"url": "git@example.com:repo.git"},
                },
            },
            {
                "name": "nogit",
                "resource": {
                    "type": "remote",
                    "host": "server",
                    "path": "/srv/nogit",
                    "workspace_path": "remote/nogit",
                },
            },
        ],
    })


class ParseProbeTest(unittest.TestCase):
    def test_parses_indexed_lines(self) -> None:
        parsed = status_module._parse_probe("R0 ok 5 on\nR1 missing 0 -\n")

        self.assertEqual(parsed[0], ("ok", "5", "on"))
        self.assertEqual(parsed[1], ("missing", "0", "-"))

    def test_ignores_malformed_lines(self) -> None:
        parsed = status_module._parse_probe("noise\nR0 ok 5 on\n")

        self.assertEqual(parsed, {0: ("ok", "5", "on")})


class FetchRemoteInfoTest(unittest.TestCase):
    def setUp(self) -> None:
        projects = _manifest().projects
        self.remote = projects[0]
        self.nogit = projects[1]

    def _info(self, project, probe):
        with patch.object(
            status_module, "inspect_mount", return_value=ResourceHealth("unmounted"),
        ):
            return status_module._fetch_remote_info(project.resource, project, probe)

    def test_ok_reports_git_and_tmux(self) -> None:
        info = self._info(self.remote, ("ok", "5", "on"))

        self.assertEqual(info.health.state, "ok")
        self.assertEqual(info.git_diff, "5 files")
        self.assertEqual(info.tmux, "on")
        self.assertEqual(info.mount, "unmounted")

    def test_nogit_resource_shows_dash(self) -> None:
        info = self._info(self.nogit, ("ok", "0", "-"))

        self.assertEqual(info.git_diff, "-")

    def test_missing_path_reports_missing(self) -> None:
        info = self._info(self.remote, ("missing", "0", "-"))

        self.assertEqual(info.health.state, "missing")

    def test_unreachable_when_probe_absent(self) -> None:
        info = self._info(self.remote, None)

        self.assertEqual(info.health.state, "unreachable")


class ProbeHostTest(unittest.TestCase):
    def test_unreachable_returns_none(self) -> None:
        project = _manifest().projects[0]
        with patch.object(
            status_module,
            "run_ssh_command",
            return_value=subprocess.CompletedProcess([], 255, "", "conn refused"),
        ):
            probe = status_module._probe_host(
                project.resource._resolved_host, [(project.resource, project)]
            )

        self.assertIsNone(probe)


if __name__ == "__main__":
    unittest.main()
