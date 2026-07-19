"""Knowledge更新Serviceの初期化・追加・削除・原子的保存テスト。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from whub.models import Manifest
from whub.services.errors import ServiceError
from whub.services.knowledge import load_project_knowledge
from whub.services.knowledge_operation import (
    add_constraint,
    add_definition,
    add_exception,
    add_policy,
    add_relation,
    add_relation_type,
    init_project_knowledge,
    remove_knowledge,
)
from whub.tests.helpers import knowledge_data, manifest_data


def _manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Manifest:
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path))
    data = manifest_data()
    local_root = tmp_path / "local-source"
    local_root.mkdir()
    data["projects"][0]["resource"]["source"] = str(local_root)
    (tmp_path / "projects" / "remote").mkdir(parents=True)
    data["projects"].append({"name": "workspace-hub"})
    return Manifest.model_validate(data)


def _write_knowledge(root: Path, data: dict | None = None) -> Path:
    path = root / "docs" / "knowledge.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data or knowledge_data(), allow_unicode=True))
    return path


def test_initializes_local_remote_and_workspace_hub(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path, monkeypatch)

    for project in ("local", "remote", "workspace-hub"):
        initialized = init_project_knowledge(manifest, project)
        assert initialized.schema_version == 3
        assert not any(
            (
                initialized.definitions,
                initialized.relation_types,
                initialized.relations,
                initialized.policies,
                initialized.constraints,
                initialized.exceptions,
            )
        )
        assert load_project_knowledge(manifest, project) == initialized

    with pytest.raises(ServiceError, match="knowledge file already exists"):
        init_project_knowledge(manifest, "local")


def test_adds_all_categories_with_max_id_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path, monkeypatch)
    data = knowledge_data()
    data["definitions"][1]["id"] = "DEF-010"
    data["relations"][0]["object"] = "DEF-010"
    _write_knowledge(tmp_path / "local-source", data)

    definition = add_definition(manifest, "local", "resource", "接続先", "docs/ref.md")
    relation_type = add_relation_type(manifest, "local", "uses", "subjectがobjectを使う")
    relation = add_relation(
        manifest,
        "local",
        definition.id,
        relation_type.name,
        "DEF-001",
        "0..*",
        "docs/ref.md",
    )
    policy = add_policy(manifest, "local", "CLIを使う", "docs/ref.md")
    constraint = add_constraint(manifest, "local", "参照を保つ", "docs/ref.md")
    exception = add_exception(
        manifest,
        "local",
        constraint.id,
        "移行中",
        "旧形式を許可する",
        "docs/ref.md",
    )

    assert definition.id == "DEF-011"
    assert relation.id == "REL-002"
    assert policy.id == "POL-002"
    assert constraint.id == "CON-002"
    assert exception.id == "EXC-002"
    loaded = load_project_knowledge(manifest, "local")
    assert loaded.definitions[-1] == definition
    assert loaded.relation_types[-1] == relation_type
    assert loaded.relations[-1] == relation
    assert loaded.policies[-1] == policy
    assert loaded.constraints[-1] == constraint
    assert loaded.exceptions[-1] == exception


def test_rejects_referenced_removal_and_removes_unreferenced_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path, monkeypatch)
    _write_knowledge(tmp_path / "local-source")

    for target, reference in (
        ("DEF-001", "REL-001"),
        ("manages", "REL-001"),
        ("CON-001", "EXC-001"),
    ):
        with pytest.raises(ServiceError, match=reference):
            remove_knowledge(manifest, "local", target)

    remove_knowledge(manifest, "local", "EXC-001")
    remove_knowledge(manifest, "local", "CON-001")
    loaded = load_project_knowledge(manifest, "local")
    assert not loaded.exceptions
    assert not loaded.constraints


def test_invalid_update_leaves_existing_file_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path, monkeypatch)
    path = _write_knowledge(tmp_path / "local-source")
    original = path.read_bytes()

    with pytest.raises(ServiceError, match="invalid Knowledge update"):
        add_relation(manifest, "local", "DEF-001", "unknown", "DEF-002")
    assert path.read_bytes() == original

    with pytest.raises(ServiceError, match="invalid Knowledge input"):
        add_definition(manifest, "local", " ", "definition")
    assert path.read_bytes() == original


def test_replace_failure_leaves_existing_file_and_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path, monkeypatch)
    path = _write_knowledge(tmp_path / "local-source")
    original = path.read_bytes()

    with (
        patch("whub.services.knowledge.os.replace", side_effect=OSError("replace failed")),
        pytest.raises(OSError, match="replace failed"),
    ):
        add_policy(manifest, "local", "保存されない")

    assert path.read_bytes() == original
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
