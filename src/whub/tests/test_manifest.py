from __future__ import annotations

import copy
import unittest
from pathlib import Path

from pydantic import ValidationError

from whub.models import Manifest


class ManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = {
            "version": "2",
            "hosts": {
                "home": {
                    "hostname": "home.example.com",
                    "user": "takumi",
                    "identity_file": "~/.ssh/id_rsa",
                },
            },
            "projects": [
                {
                    "name": "local",
                    "resource": {
                        "type": "symlink",
                        "workspace_path": "projects/local",
                        "source": "/Users/takumi/projects/local",
                    },
                },
                {
                    "name": "remote",
                    "resource": {
                        "type": "remote",
                        "host": "home",
                        "path": "",
                    },
                },
                {
                    "name": "workspace-hub",
                },
            ],
        }

    def test_accepts_project_without_resource(self) -> None:
        manifest = Manifest.model_validate(self.data)

        self.assertEqual(
            [project.name for project in manifest.projects],
            ["local", "remote", "workspace-hub"],
        )
        self.assertIsNone(manifest.projects[2].resource)

    def test_rejects_workspace_path_outside_root(self) -> None:
        for value in ("/absolute", "../outside", "projects/../../outside"):
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["projects"][0]["resource"]["workspace_path"] = value
                with self.assertRaises(ValidationError):
                    Manifest.model_validate(data)

    def test_requires_absolute_source_and_remote_path(self) -> None:
        invalid_fields = (
            (0, "source", "relative/source"),
            (0, "source", "~/source"),
            (1, "path", "relative/path"),
            (1, "path", "~/path"),
        )
        for project_index, field, value in invalid_fields:
            with self.subTest(project_index=project_index, field=field, value=value):
                data = copy.deepcopy(self.data)
                data["projects"][project_index]["resource"][field] = value
                with self.assertRaises(ValidationError):
                    Manifest.model_validate(data)

    def test_rejects_unknown_host_and_duplicate_project_name(self) -> None:
        data = copy.deepcopy(self.data)
        data["projects"][1]["resource"]["host"] = "missing"
        with self.assertRaisesRegex(ValidationError, "unknown host"):
            Manifest.model_validate(data)

        data = copy.deepcopy(self.data)
        data["projects"][1]["name"] = "local"
        with self.assertRaisesRegex(ValidationError, "duplicate project names"):
            Manifest.model_validate(data)

    def test_rejects_legacy_and_unknown_fields(self) -> None:
        data = copy.deepcopy(self.data)
        data["hosts"]["home"]["auto_mount"] = True
        with self.assertRaises(ValidationError):
            Manifest.model_validate(data)

        with self.assertRaises(ValidationError):
            Manifest.model_validate({
                "version": "1",
                "resources": {
                    "symlinks": [
                        {
                            "name": "legacy",
                            "workspace_path": "legacy",
                            "source": "/tmp/legacy",
                        },
                    ],
                },
            })

    def test_rejects_mismatched_resource_shape(self) -> None:
        data = copy.deepcopy(self.data)
        data["projects"][0]["resource"] = {
            "type": "remote",
            "workspace_path": "projects/local",
            "source": "/Users/takumi/projects/local",
        }
        with self.assertRaises(ValidationError):
            Manifest.model_validate(data)

    def test_resolves_workspace_path(self) -> None:
        manifest = Manifest.model_validate(self.data)
        manifest._root = Path("/workspace")

        self.assertEqual(
            manifest.resolve_path("projects/local"),
            Path("/workspace/projects/local"),
        )
        self.assertEqual(manifest.workspace_root, Path("/workspace"))

    def test_resolves_project(self) -> None:
        manifest = Manifest.model_validate(self.data)

        self.assertEqual(manifest.resolve_project("local").name, "local")
        self.assertIsNone(manifest.resolve_project("missing"))


if __name__ == "__main__":
    unittest.main()
