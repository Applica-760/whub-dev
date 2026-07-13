"""Knowledge Serviceのproject解決・読込・検索テスト。

検証するケース:
1. local・remote・workspace-hubのKnowledgeを読む。
2. project不明・resourceなし・ファイル不在・remote未接続を通知する。
3. schema不正をServiceErrorへ変換する。
4. Definition・Constraintと直接関係するエントリを検索する。
5. Relation type名・定義と利用Relationを相互に検索する。
6. 空検索を拒否し、一致なしを空結果で返す。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.knowledge import load_project_knowledge, query_knowledge
from whub.tests.helpers import knowledge, knowledge_data, manifest_data


def _write_knowledge(root: Path) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "knowledge.yaml").write_text(
        yaml.safe_dump(knowledge_data(), allow_unicode=True),
    )


def test_loads_local_remote_and_workspace_hub_knowledge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ケース1
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path))
    data = manifest_data()
    local_source = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_source)
    _write_knowledge(local_source)
    _write_knowledge(tmp_path / "projects" / "remote")
    data["projects"].append({"name": "workspace-hub"})
    _write_knowledge(tmp_path)
    loaded_manifest = Manifest.model_validate(data)

    assert load_project_knowledge(loaded_manifest, "local").definitions[0].name == "whub"
    assert load_project_knowledge(loaded_manifest, "remote").relations[0].id == "REL-001"
    assert load_project_knowledge(loaded_manifest, "workspace-hub").policies[0].id == "POL-001"


def test_reports_project_and_file_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ケース2
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path))
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


def test_query_matches_text_and_includes_direct_relations_and_exceptions() -> None:
    # ケース4
    by_definition = query_knowledge(knowledge(), "PROJECT")
    assert [entry.id for entry in by_definition.definitions] == ["DEF-002"]
    assert [entry.id for entry in by_definition.relations] == ["REL-001"]

    by_constraint = query_knowledge(knowledge(), "CON-001")
    assert [entry.id for entry in by_constraint.constraints] == ["CON-001"]
    assert [entry.id for entry in by_constraint.exceptions] == ["EXC-001"]

    # ケース5
    by_relation_type = query_knowledge(knowledge(), "subjectがobjectを管理する")
    assert [item.name for item in by_relation_type.relation_types] == ["manages"]
    assert [entry.id for entry in by_relation_type.relations] == ["REL-001"]

    by_relation = query_knowledge(knowledge(), "REL-001")
    assert [item.name for item in by_relation.relation_types] == ["manages"]

    # ケース6
    assert query_knowledge(knowledge(), "not-found").is_empty()
    with pytest.raises(ServiceError, match="knowledge query term is required"):
        query_knowledge(knowledge(), "  ")
