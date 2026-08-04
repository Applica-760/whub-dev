from __future__ import annotations

from pathlib import Path

from whub.models import Manifest
from whub.services.manifest import resolve_manifest


def manifest_data() -> dict:
    return {
        "version": "2",
        "hosts": {
            "home": {
                "hostname": "home.example.com",
                "user": "takumi",
                "port": 2222,
                "identity_file": "~/.ssh/id_home",
                "mount_root": "/srv",
            },
        },
        "projects": [
            {
                "name": "local",
                "resource": {
                    "type": "symlink",
                    "workspace_path": "projects/local",
                    "source": "/tmp/local-source",
                },
            },
            {
                "name": "remote",
                "resource": {
                    "type": "remote",
                    "host": "home",
                    "path": "remote",
                    "workspace_path": "projects/remote",
                },
            },
            {
                "name": "nested",
                "resource": {
                    "type": "remote",
                    "host": "home",
                    "path": "remote/nested",
                    "workspace_path": "projects/remote/nested",
                },
            },
            {"name": "no-resource"},
        ],
    }


def manifest() -> Manifest:
    return resolve_manifest(Manifest.model_validate(manifest_data()), Path("/tmp"))
