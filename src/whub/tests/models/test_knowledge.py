"""Knowledge YAMLモデルとローダーの仕様テスト。

検証するケース:
1. schema v4のslug mappingと複合Relationを受理する。
2. slug形式違反と未知フィールドを拒否する。
3. Relation複合キーの重複を拒否する。
4. Relationの参照切れとpredicate形式違反を拒否する。
5. Exceptionの参照切れを拒否する。
6. loaderはファイル・YAML・重複key・schema不正をKnowledgeErrorにする。
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from whub.models import Knowledge, KnowledgeError, load_knowledge
from whub.tests.helpers import knowledge_data


def test_validates_all_knowledge_categories() -> None:
    # ケース1
    loaded = Knowledge.model_validate(knowledge_data())

    assert loaded.schema_version == 4
    assert loaded.definitions["whub"].name == "whub"
    assert loaded.relations[0].subject == "def:whub"
    assert loaded.policies["knowledge_is_ssot"].statement
    assert loaded.constraints["reject_unknown_fields"].statement
    assert (
        loaded.exceptions["legacy_document_transition"].exception_to
        == "con:reject_unknown_fields"
    )


def test_rejects_invalid_slug_and_unknown_fields() -> None:
    # ケース2
    invalid_slug = knowledge_data()
    invalid_slug["definitions"]["Invalid-Slug"] = invalid_slug["definitions"].pop(
        "whub"
    )
    with pytest.raises(ValidationError):
        Knowledge.model_validate(invalid_slug)

    unknown_field = knowledge_data()
    unknown_field["definitions"]["whub"]["summary"] = "unsupported"
    with pytest.raises(ValidationError):
        Knowledge.model_validate(unknown_field)


def test_rejects_duplicate_relations() -> None:
    # ケース3
    data = knowledge_data()
    data["relations"].append(copy.deepcopy(data["relations"][0]))

    with pytest.raises(
        ValidationError,
        match="duplicate knowledge relations: def:whub manages def:project",
    ):
        Knowledge.model_validate(data)


def test_rejects_unknown_relation_references() -> None:
    # ケース4
    data = knowledge_data()
    data["relations"][0]["object"] = "def:missing"

    with pytest.raises(
        ValidationError,
        match="references unknown knowledge entries: def:missing",
    ):
        Knowledge.model_validate(data)


def test_rejects_invalid_relation_predicates() -> None:
    # ケース4
    data = knowledge_data()
    data["relations"][0]["predicate"] = "invalid-predicate"

    with pytest.raises(ValidationError):
        Knowledge.model_validate(data)


def test_rejects_unknown_exception_target() -> None:
    # ケース5
    data = knowledge_data()
    data["exceptions"]["legacy_document_transition"]["exception_to"] = "pol:missing"

    with pytest.raises(
        ValidationError,
        match="references unknown policy or constraint: pol:missing",
    ):
        Knowledge.model_validate(data)


def test_load_knowledge_reports_file_yaml_and_schema_errors(tmp_path: Path) -> None:
    # ケース6
    valid_path = tmp_path / "knowledge.yaml"
    valid_path.write_text(yaml.safe_dump(knowledge_data(), allow_unicode=True))
    assert load_knowledge(valid_path).definitions["whub"].name == "whub"

    with pytest.raises(KnowledgeError, match="failed to load Knowledge YAML"):
        load_knowledge(tmp_path / "missing.yaml")

    valid_path.write_text("schema_version: [")
    with pytest.raises(KnowledgeError, match="failed to load Knowledge YAML"):
        load_knowledge(valid_path)

    valid_path.write_text("schema_version: 1\n")
    with pytest.raises(KnowledgeError, match="failed to load Knowledge YAML"):
        load_knowledge(valid_path)

    valid_path.write_text(
        """
schema_version: 4
definitions:
  duplicate:
    name: first
    definition: first
  duplicate:
    name: second
    definition: second
relations: []
policies: {}
constraints: {}
exceptions: {}
""".lstrip()
    )
    with pytest.raises(KnowledgeError, match="found duplicate key: duplicate"):
        load_knowledge(valid_path)
