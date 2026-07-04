from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands import fetch as fetch_module
from whub.models import Manifest
from whub.target import TargetError, resolve_resource_by_workspace_path


def _manifest() -> Manifest:
    return Manifest.model_validate({
        "version": "2",
        "hosts": {
            "server": {
                "hostname": "example.com",
                "user": "user",
                "port": 2222,
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
            {"name": "workspace-hub"},
        ],
    })


class ResolveResourceByWorkspacePathTest(unittest.TestCase):
    def test_resolves_resource_and_relative_path(self) -> None:
        project, resource, rel = resolve_resource_by_workspace_path(
            _manifest(),
            "remote/remote/data/run1/out.nc",
        )

        self.assertEqual(project.name, "remote")
        self.assertEqual(resource.path, "/srv/remote")
        self.assertEqual(rel, "data/run1/out.nc")

    def test_resource_root_returns_empty_relative_path(self) -> None:
        _, _, rel = resolve_resource_by_workspace_path(_manifest(), "remote/remote")

        self.assertEqual(rel, "")

    def test_rejects_absolute_escaping_and_uncontained_paths(self) -> None:
        for path in ("/etc/passwd", "remote/../secret", "elsewhere/file", "remote"):
            with self.subTest(path=path):
                with self.assertRaises(TargetError):
                    resolve_resource_by_workspace_path(_manifest(), path)


class FetchCommandTest(unittest.TestCase):
    def _invoke(self, path: str, *, returncode: int = 0):
        runner = CliRunner()
        completed = subprocess.CompletedProcess([], returncode)
        with runner.isolated_filesystem():
            with patch.object(
                fetch_module.subprocess,
                "run",
                return_value=completed,
            ) as execute:
                result = runner.invoke(
                    fetch_module.fetch,
                    [path],
                    obj={"manifest": _manifest()},
                )
        return result, execute

    def test_fetches_file_flat_into_downloads(self) -> None:
        result, execute = self._invoke("remote/remote/data/run1/out.nc")

        self.assertEqual(result.exit_code, 0)
        execute.assert_called_once_with([
            "scp",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            "-i", "/tmp/key",
            "-P", "2222",
            "user@example.com:/srv/remote/data/run1/out.nc",
            str(Path(".whub/downloads/out.nc")),
        ])

    def test_rejects_local_resource(self) -> None:
        result, execute = self._invoke("projects/local/file.txt")

        self.assertEqual(result.exit_code, 1)
        self.assertIn("not a remote resource: local", result.output)
        execute.assert_not_called()

    def test_rejects_resource_root(self) -> None:
        result, execute = self._invoke("remote/remote")

        self.assertEqual(result.exit_code, 1)
        self.assertIn("must point to a file", result.output)
        execute.assert_not_called()

    def test_passes_through_scp_exit_code(self) -> None:
        result, _ = self._invoke("remote/remote/out.nc", returncode=42)

        self.assertEqual(result.exit_code, 42)


if __name__ == "__main__":
    unittest.main()
