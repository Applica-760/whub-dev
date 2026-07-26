from __future__ import annotations

from whub.models import Manifest


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
    return Manifest.model_validate(manifest_data())
