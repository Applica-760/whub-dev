"""`whub knowledge`の件数表示・YAML出力・エラー変換テスト。

検証するケース:
1. checkがRelation typeを含む分類件数を表示する。
2. queryがRelation typeと直接関係をYAMLで返す。
3. query一致なしをエラー表示する。
4. ServiceErrorをClickExceptionへ変換する。
"""
from __future__ import annotations

from unittest.mock import patch

import yaml
from click.testing import CliRunner

from whub.commands.knowledge import knowledge as knowledge_command
from whub.services.errors import ServiceError
from whub.tests.helpers import knowledge, manifest


def test_check_displays_category_counts() -> None:
    # ケース1
    loaded_manifest = manifest()
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch(
            "whub.commands.knowledge.load_project_knowledge",
            return_value=knowledge(),
        ) as mock_load,
    ):
        result = CliRunner().invoke(
            knowledge_command,
            ["check", "local"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert result.output.strip() == (
        "valid local: 2 definitions, 1 relation types, 1 relations, 1 policies, "
        "1 constraints, 1 exceptions"
    )
    mock_load.assert_called_once_with(loaded_manifest, "local")


def test_query_outputs_matching_groups_as_yaml() -> None:
    # ケース2
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=manifest()),
        patch("whub.commands.knowledge.load_project_knowledge", return_value=knowledge()),
    ):
        result = CliRunner().invoke(
            knowledge_command,
            ["query", "PROJECT", "local"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    output = yaml.safe_load(result.output)
    assert [entry["id"] for entry in output["definitions"]] == ["DEF-002"]
    assert [item["name"] for item in output["relation_types"]] == ["manages"]
    assert [entry["id"] for entry in output["relations"]] == ["REL-001"]
    assert set(output) == {"definitions", "relation_types", "relations"}


def test_query_reports_no_matches() -> None:
    # ケース3
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=manifest()),
        patch("whub.commands.knowledge.load_project_knowledge", return_value=knowledge()),
    ):
        result = CliRunner().invoke(
            knowledge_command,
            ["query", "not-found", "local"],
        )

    assert result.exit_code != 0
    assert "no knowledge matches: not-found" in result.output


def test_check_converts_service_error_to_click_error() -> None:
    # ケース4
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=manifest()),
        patch(
            "whub.commands.knowledge.load_project_knowledge",
            side_effect=ServiceError("knowledge unavailable"),
        ),
    ):
        result = CliRunner().invoke(knowledge_command, ["check", "local"])

    assert result.exit_code != 0
    assert "knowledge unavailable" in result.output
