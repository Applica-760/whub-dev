from __future__ import annotations
from pathlib import Path
from whub.models import Knowledge, Manifest

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


def knowledge_data() -> dict:
    return {
        "schema_version": 3,
        "definitions": [
            {
                "id": "DEF-001",
                "name": "whub",
                "definition": "localとremoteを統合管理するCLI",
            },
            {
                "id": "DEF-002",
                "name": "project",
                "definition": "管理対象のプロジェクト",
                "ref": "docs/knowledge.yaml",
            },
        ],
        "relation_types": [
            {
                "name": "manages",
                "definition": "subjectがobjectを管理する",
            },
        ],
        "relations": [
            {
                "id": "REL-001",
                "subject": "DEF-001",
                "predicate": "manages",
                "object": "DEF-002",
                "cardinality": "1..*",
            },
        ],
        "policies": [
            {"id": "POL-001", "statement": "Knowledge YAMLをSSOTとする"},
        ],
        "constraints": [
            {"id": "CON-001", "statement": "未知フィールドを拒否する"},
        ],
        "exceptions": [
            {
                "id": "EXC-001",
                "exception_to": "CON-001",
                "condition": "移行期間中",
                "statement": "旧文書への導線を残せる",
            },
        ],
    }


def knowledge() -> Knowledge:
    return Knowledge.model_validate(knowledge_data())


def write_config(root: Path, data_dir: Path) -> None:
    config_dir = root / ".whub"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(f'data_dir = "{data_dir}"\n')
