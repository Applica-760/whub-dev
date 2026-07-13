"""Knowledge YAMLモデルとローダーの仕様テスト。

検証するケース:
1. schema v3の全分類とRelation typeを受理する。
2. ID種別違反と未知フィールドを拒否する。
3. Knowledge IDとRelation type名の重複を拒否する。
4. Relationの参照切れと未登録predicateを拒否する。
5. Exceptionの参照切れを拒否する。
6. loaderはファイル・YAML・schema不正をKnowledgeErrorにする。
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

    assert loaded.schema_version == 3
    assert loaded.definitions[0].id == "DEF-001"
    assert loaded.relation_types[0].name == "manages"
    assert loaded.relations[0].id == "REL-001"
    assert loaded.policies[0].id == "POL-001"
    assert loaded.constraints[0].id == "CON-001"
    assert loaded.exceptions[0].id == "EXC-001"


def test_rejects_wrong_id_type_and_unknown_fields() -> None:
    # ケース2
    wrong_id = knowledge_data()
    wrong_id["policies"][0]["id"] = "DEF-003"
    with pytest.raises(ValidationError):
        Knowledge.model_validate(wrong_id)

    unknown_field = knowledge_data()
    unknown_field["definitions"][0]["summary"] = "unsupported"
    with pytest.raises(ValidationError):
        Knowledge.model_validate(unknown_field)


def test_rejects_duplicate_ids() -> None:
    # ケース3
    data = knowledge_data()
    data["definitions"].append(copy.deepcopy(data["definitions"][0]))

    with pytest.raises(ValidationError, match="duplicate knowledge ids: DEF-001"):
        Knowledge.model_validate(data)


def test_rejects_duplicate_relation_type_names() -> None:
    # ケース3
    data = knowledge_data()
    data["relation_types"].append(copy.deepcopy(data["relation_types"][0]))

    with pytest.raises(ValidationError, match="duplicate relation type names: manages"):
        Knowledge.model_validate(data)


def test_rejects_unknown_relation_references() -> None:
    # ケース4
    data = knowledge_data()
    data["relations"][0]["object"] = "DEF-999"

    with pytest.raises(ValidationError, match="references unknown knowledge ids: DEF-999"):
        Knowledge.model_validate(data)


def test_rejects_unknown_relation_predicates() -> None:
    # ケース4
    data = knowledge_data()
    data["relations"][0]["predicate"] = "unknown"

    with pytest.raises(ValidationError, match="unknown relation predicates: unknown"):
        Knowledge.model_validate(data)


def test_rejects_unknown_exception_target() -> None:
    # ケース5
    data = knowledge_data()
    data["exceptions"][0]["exception_to"] = "POL-999"

    with pytest.raises(
        ValidationError,
        match="references unknown policy or constraint: POL-999",
    ):
        Knowledge.model_validate(data)


def test_load_knowledge_reports_file_yaml_and_schema_errors(tmp_path: Path) -> None:
    # ケース6
    valid_path = tmp_path / "knowledge.yaml"
    valid_path.write_text(yaml.safe_dump(knowledge_data(), allow_unicode=True))
    assert load_knowledge(valid_path).definitions[0].name == "whub"

    with pytest.raises(KnowledgeError, match="failed to load Knowledge YAML"):
        load_knowledge(tmp_path / "missing.yaml")

    valid_path.write_text("schema_version: [")
    with pytest.raises(KnowledgeError, match="failed to load Knowledge YAML"):
        load_knowledge(valid_path)

    valid_path.write_text("schema_version: 1\n")
    with pytest.raises(KnowledgeError, match="failed to load Knowledge YAML"):
        load_knowledge(valid_path)
