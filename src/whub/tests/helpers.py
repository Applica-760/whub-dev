from __future__ import annotations

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


def knowledge_data() -> dict:
    return {
        "schema_version": 4,
        "definitions": {
            "whub": {
                "name": "whub",
                "definition": "localとremoteを統合管理するCLI",
            },
            "project": {
                "name": "project",
                "definition": "管理対象のプロジェクト",
                "ref": "docs/knowledge.yaml",
            },
        },
        "relations": [
            {
                "subject": "def:whub",
                "predicate": "manages",
                "object": "def:project",
                "cardinality": "1..*",
            },
        ],
        "policies": {
            "knowledge_is_ssot": {"statement": "Knowledge YAMLをSSOTとする"},
        },
        "constraints": {
            "reject_unknown_fields": {"statement": "未知フィールドを拒否する"},
        },
        "exceptions": {
            "legacy_document_transition": {
                "exception_to": "con:reject_unknown_fields",
                "condition": "移行期間中",
                "statement": "旧文書への導線を残せる",
            },
        },
    }


def knowledge() -> Knowledge:
    return Knowledge.model_validate(knowledge_data())
