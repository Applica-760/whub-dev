from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import click

from whub import health
from whub.commands.mount import _mount_one, _select_targets
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
                "name": "local",
                "resource": {
                    "type": "symlink",
                    "workspace_path": "projects/local",
                    "source": "/tmp/local",
                },
            },
            {
                "name": "remote",
                "resource": {
                    "type": "remote",
                    "host": "server",
                    "path": "/srv/remote",
                    "workspace_path": "remote/remote",
                },
            },
            {
                "name": "hpc",
                "resource": {
                    "type": "remote",
                    "host": "server",
                    "path": "/srv/hpc",
                    "workspace_path": "remote/hpc",
                    "mount": False,
                },
            },
            {"name": "workspace-hub"},
        ],
    })


class SelectTargetsTest(unittest.TestCase):
    def test_selects_all_remote_resources(self) -> None:
        targets = _select_targets(_manifest(), None)

        self.assertEqual([project.name for project, _ in targets], ["remote", "hpc"])

    def test_auto_only_excludes_mount_false(self) -> None:
        targets = _select_targets(_manifest(), None, auto_only=True)

        self.assertEqual([project.name for project, _ in targets], ["remote"])

    def test_selects_named_remote_project_ignoring_mount_flag(self) -> None:
        for name in ("remote", "hpc"):
            with self.subTest(name=name):
                targets = _select_targets(_manifest(), name, auto_only=True)

                self.assertEqual([project.name for project, _ in targets], [name])

    def test_rejects_unknown_and_non_remote_project(self) -> None:
        for name in ("missing", "local", "workspace-hub"):
            with self.subTest(name=name):
                with self.assertRaises(click.ClickException):
                    _select_targets(_manifest(), name)


class MountCommandTest(unittest.TestCase):
    def test_mount_failure_keeps_existing_mountpoint(self) -> None:
        project = _manifest().projects[1]
        resource = project.resource
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp) / "mountpoint"
            mountpoint.mkdir()
            resource._resolved_workspace_path = mountpoint
            with (
                patch(
                    "whub.commands.mount.inspect_mount",
                    return_value=health.ResourceHealth("unmounted"),
                ),
                patch("whub.commands.mount.build_sshfs_command", return_value=["sshfs"]),
                patch(
                    "whub.commands.mount.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 1, "", "failed"),
                ),
            ):
                status = _mount_one(project, resource)

            self.assertEqual(status, "FAIL: failed")
            self.assertTrue(mountpoint.exists())

    def test_mount_failure_removes_created_mountpoint(self) -> None:
        project = _manifest().projects[1]
        resource = project.resource
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp) / "mountpoint"
            resource._resolved_workspace_path = mountpoint
            with (
                patch(
                    "whub.commands.mount.inspect_mount",
                    return_value=health.ResourceHealth("unmounted"),
                ),
                patch("whub.commands.mount.build_sshfs_command", return_value=["sshfs"]),
                patch(
                    "whub.commands.mount.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 1, "", "failed"),
                ),
            ):
                status = _mount_one(project, resource)

            self.assertEqual(status, "FAIL: failed")
            self.assertFalse(mountpoint.exists())


class InspectMountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.resource = _manifest().projects[1].resource
        self.mountpoint = self.resource._resolved_workspace_path

    def _mount_table(self, mounted: bool) -> subprocess.CompletedProcess[str]:
        stdout = f"server:/srv/remote on {self.mountpoint} (nfs)\n" if mounted else ""
        return subprocess.CompletedProcess([], 0, stdout, "")

    def test_reports_unmounted(self) -> None:
        with patch.object(
            health.subprocess,
            "run",
            return_value=self._mount_table(mounted=False),
        ):
            self.assertEqual(health.inspect_mount(self.resource).state, "unmounted")

    def test_reports_ok_when_stat_succeeds(self) -> None:
        stat_ok = subprocess.CompletedProcess([], 0, b"", b"")
        with patch.object(
            health.subprocess,
            "run",
            side_effect=[self._mount_table(mounted=True), stat_ok],
        ):
            self.assertEqual(health.inspect_mount(self.resource).state, "ok")

    def test_reports_stale_when_stat_times_out(self) -> None:
        with patch.object(
            health.subprocess,
            "run",
            side_effect=[
                self._mount_table(mounted=True),
                subprocess.TimeoutExpired(["stat"], 3),
            ],
        ):
            self.assertEqual(health.inspect_mount(self.resource).state, "stale")

    def test_reports_stale_when_mount_listing_times_out(self) -> None:
        with patch.object(
            health.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["mount"], 5),
        ):
            self.assertEqual(health.inspect_mount(self.resource).state, "stale")

    def test_reports_stale_when_mount_listing_fails(self) -> None:
        with patch.object(
            health.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 1, "", "mount failed"),
        ):
            self.assertEqual(health.inspect_mount(self.resource).state, "stale")


if __name__ == "__main__":
    unittest.main()
