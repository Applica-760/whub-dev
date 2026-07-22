"""Knowledge Serviceのproject解決・読込・検索テスト。

検証するケース:
1. local・remote ProjectのKnowledgeを読む。
2. project不明・resourceなし・ファイル不在・remote未接続を通知する。
3. schema不正をServiceErrorへ変換する。
4. Definition・Constraintと直接関係するエントリを検索する。
5. Relationのpredicateと複合キーを検索する。
6. 空検索を拒否し、一致なしを空結果で返す。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.knowledge import (
    check_project_knowledge,
    load_project_knowledge,
    query_knowledge,
)
from whub.tests.helpers import knowledge, knowledge_data, manifest_data


def _write_knowledge(root: Path, data: dict | None = None) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "knowledge.yaml").write_text(
        yaml.safe_dump(data or knowledge_data(), allow_unicode=True),
    )


def test_loads_local_and_remote_knowledge(
    tmp_path: Path,
) -> None:
    # ケース1
    data = manifest_data()
    local_source = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_source)
    _write_knowledge(local_source)
    _write_knowledge(tmp_path / "projects" / "remote")
    loaded_manifest = Manifest.model_validate(data)

    assert (
        load_project_knowledge(loaded_manifest, "local").definitions["whub"].name
        == "whub"
    )
    assert (
        load_project_knowledge(loaded_manifest, "remote").relations[0].subject
        == "def:whub"
    )


def test_reports_project_and_file_errors(
    tmp_path: Path,
) -> None:
    # ケース2
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(tmp_path / "missing-local")
    loaded_manifest = Manifest.model_validate(data)

    with pytest.raises(ServiceError, match="unknown project: missing"):
        load_project_knowledge(loaded_manifest, "missing")
    with pytest.raises(ServiceError, match="project has no resource: no-resource"):
        load_project_knowledge(loaded_manifest, "no-resource")
    with pytest.raises(NotFoundError, match="knowledge file not found"):
        load_project_knowledge(loaded_manifest, "local")
    with pytest.raises(ServiceError, match="remote workspace path is not available"):
        load_project_knowledge(loaded_manifest, "remote")


def test_converts_invalid_knowledge_to_service_error(tmp_path: Path) -> None:
    # ケース3
    data = manifest_data()
    local_source = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_source)
    docs = local_source / "docs"
    docs.mkdir(parents=True)
    (docs / "knowledge.yaml").write_text("schema_version: [")

    with pytest.raises(ServiceError, match="failed to load Knowledge YAML"):
        load_project_knowledge(Manifest.model_validate(data), "local")


def test_check_validates_project_relative_refs(
    tmp_path: Path,
) -> None:
    manifest_input = manifest_data()
    local_source = tmp_path / "local-source"
    manifest_input["projects"][0]["resource"]["source"] = str(local_source)
    data = knowledge_data()
    data["definitions"]["project"]["ref"] = "docs/reference.md#section"
    data["policies"]["knowledge_is_ssot"]["ref"] = "https://example.com/knowledge"
    _write_knowledge(local_source, data)
    (local_source / "docs" / "reference.md").write_text("reference")
    loaded_manifest = Manifest.model_validate(manifest_input)

    assert check_project_knowledge(loaded_manifest, "local").schema_version == 4

    data["definitions"]["project"]["ref"] = "docs/missing.md"
    (local_source / "docs" / "knowledge.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True)
    )
    with pytest.raises(
        ServiceError,
        match=r"def:project: docs/missing\.md",
    ):
        check_project_knowledge(loaded_manifest, "local")

    data["definitions"]["project"]["ref"] = "../outside.md"
    (local_source / "docs" / "knowledge.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True)
    )
    with pytest.raises(ServiceError, match="escapes project root"):
        check_project_knowledge(loaded_manifest, "local")


def test_query_matches_text_and_includes_direct_relations_and_exceptions() -> None:
    # ケース4
    by_definition = query_knowledge(knowledge(), "PROJECT")
    assert list(by_definition.definitions) == ["project"]
    assert [entry.predicate for entry in by_definition.relations] == ["manages"]

    by_constraint = query_knowledge(knowledge(), "con:reject_unknown_fields")
    assert list(by_constraint.constraints) == ["reject_unknown_fields"]
    assert list(by_constraint.exceptions) == ["legacy_document_transition"]

    # ケース5
    by_predicate = query_knowledge(knowledge(), "manages")
    assert [entry.predicate for entry in by_predicate.relations] == ["manages"]

    by_relation = query_knowledge(knowledge(), "def:whub")
    assert [entry.object for entry in by_relation.relations] == ["def:project"]

    # ケース6
    assert query_knowledge(knowledge(), "not-found").is_empty()
    with pytest.raises(ServiceError, match="knowledge query term is required"):
        query_knowledge(knowledge(), "  ")
