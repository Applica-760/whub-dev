from __future__ import annotations
from pathlib import Path
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
                    "path": "/srv/remote",
                    "workspace_path": "projects/remote",
                },
            },
            {
                "name": "nested",
                "resource": {
                    "type": "remote",
                    "host": "home",
                    "path": "/srv/remote/nested",
                    "workspace_path": "projects/remote/nested",
                    "mount": False,
                },
            },
            {"name": "no-resource"},
        ],
    }


def manifest() -> Manifest:
    return Manifest.model_validate(manifest_data())


def write_config(root: Path, data_dir: Path) -> None:
    config_dir = root / ".whub"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(f'data_dir = "{data_dir}"\n')
