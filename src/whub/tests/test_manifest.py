from __future__ import annotations

import copy
import unittest

from pydantic import ValidationError

from whub.models import Manifest


class ManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = {
            "version": "1",
            "hosts": {
                "home": {
                    "hostname": "home.example.com",
                    "user": "takumi",
                    "identity_file": "~/.ssh/id_rsa",
                },
            },
            "resources": {
                "symlinks": [
                    {
                        "name": "local",
                        "workspace_path": "projects/local",
                        "source": "/Users/takumi/projects/local",
                    },
                ],
                "remotes": [
                    {
                        "name": "remote",
                        "host": "home",
                        "path": "",
                    },
                ],
            },
        }

    def test_rejects_workspace_path_outside_root(self) -> None:
        for value in ("/absolute", "../outside", "projects/../../outside"):
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["resources"]["symlinks"][0]["workspace_path"] = value
                with self.assertRaises(ValidationError):
                    Manifest.model_validate(data)

    def test_requires_absolute_source_and_remote_path(self) -> None:
        invalid_fields = (
            ("symlinks", "source", "relative/source"),
            ("symlinks", "source", "~/source"),
            ("remotes", "path", "relative/path"),
            ("remotes", "path", "~/path"),
        )
        for resource_type, field, value in invalid_fields:
            with self.subTest(resource_type=resource_type, field=field, value=value):
                data = copy.deepcopy(self.data)
                data["resources"][resource_type][0][field] = value
                with self.assertRaises(ValidationError):
                    Manifest.model_validate(data)

    def test_rejects_unknown_host_and_duplicate_resource_name(self) -> None:
        data = copy.deepcopy(self.data)
        data["resources"]["remotes"][0]["host"] = "missing"
        with self.assertRaisesRegex(ValidationError, "unknown host"):
            Manifest.model_validate(data)

        data = copy.deepcopy(self.data)
        data["resources"]["remotes"][0]["name"] = "local"
        with self.assertRaisesRegex(ValidationError, "duplicate resource names"):
            Manifest.model_validate(data)

    def test_rejects_legacy_and_unknown_fields(self) -> None:
        data = copy.deepcopy(self.data)
        data["hosts"]["home"]["auto_mount"] = True
        with self.assertRaises(ValidationError):
            Manifest.model_validate(data)

        with self.assertRaises(ValidationError):
            Manifest.model_validate({
                "version": "1",
                "resources": [{"name": "legacy", "type": "mount"}],
            })


if __name__ == "__main__":
    unittest.main()
