"""`whub knowledge` CLIの読取り・更新境界テスト。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from whub.commands.knowledge import knowledge as knowledge_command
from whub.services.errors import ServiceError
from whub.tests.helpers import knowledge, manifest


def test_check_defaults_to_workspace_hub() -> None:
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
            ["check"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert result.output.strip() == (
        "valid workspace-hub: 2 definitions, 1 relation types, 1 relations, "
        "1 policies, 1 constraints, 1 exceptions"
    )
    mock_load.assert_called_once_with(loaded_manifest, "workspace-hub")


def test_query_accepts_project_option_and_outputs_yaml() -> None:
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
            ["query", "PROJECT", "--project", "local"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    output = yaml.safe_load(result.output)
    assert [entry["id"] for entry in output["definitions"]] == ["DEF-002"]
    assert [item["name"] for item in output["relation_types"]] == ["manages"]
    assert [entry["id"] for entry in output["relations"]] == ["REL-001"]
    assert set(output) == {"definitions", "relation_types", "relations"}
    mock_load.assert_called_once_with(loaded_manifest, "local")


def test_init_and_ls_use_one_project_and_category() -> None:
    loaded_manifest = manifest()
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch("whub.commands.knowledge.init_project_knowledge") as mock_init,
    ):
        initialized = CliRunner().invoke(
            knowledge_command,
            ["init", "--project", "local"],
            catch_exceptions=False,
        )

    assert initialized.exit_code == 0
    assert initialized.output.strip() == "initialized local"
    mock_init.assert_called_once_with(loaded_manifest, "local")

    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch(
            "whub.commands.knowledge.load_project_knowledge",
            return_value=knowledge(),
        ),
    ):
        listed = CliRunner().invoke(
            knowledge_command,
            ["ls", "con"],
            catch_exceptions=False,
        )

    assert listed.exit_code == 0
    assert yaml.safe_load(listed.output) == {
        "constraints": [
            {"id": "CON-001", "statement": "未知フィールドを拒否する"},
        ],
    }
    missing_category = CliRunner().invoke(knowledge_command, ["ls"])
    assert missing_category.exit_code != 0
    assert "Missing argument" in missing_category.output


@pytest.mark.parametrize(
    ("arguments", "function_name", "expected_call", "identifier"),
    [
        (
            ["def", "resource", "接続先", "--ref", "docs/ref.md"],
            "add_definition",
            ("resource", "接続先", "docs/ref.md"),
            "DEF-002",
        ),
        (
            ["relation-type", "uses", "subjectがobjectを使う"],
            "add_relation_type",
            ("uses", "subjectがobjectを使う"),
            None,
        ),
        (
            [
                "rel",
                "DEF-001",
                "uses",
                "DEF-002",
                "--cardinality",
                "0..*",
                "--ref",
                "docs/ref.md",
            ],
            "add_relation",
            ("DEF-001", "uses", "DEF-002", "0..*", "docs/ref.md"),
            "REL-002",
        ),
        (
            ["pol", "CLIを使う", "--ref", "docs/ref.md"],
            "add_policy",
            ("CLIを使う", "docs/ref.md"),
            "POL-002",
        ),
        (
            ["con", "参照を保つ", "--ref", "docs/ref.md"],
            "add_constraint",
            ("参照を保つ", "docs/ref.md"),
            "CON-002",
        ),
        (
            [
                "exc",
                "CON-001",
                "移行中",
                "旧形式を許可する",
                "--ref",
                "docs/ref.md",
            ],
            "add_exception",
            ("CON-001", "移行中", "旧形式を許可する", "docs/ref.md"),
            "EXC-002",
        ),
    ],
)
def test_add_dispatches_category_specific_arguments(
    arguments: list[str],
    function_name: str,
    expected_call: tuple[str, ...],
    identifier: str | None,
) -> None:
    loaded_manifest = manifest()
    returned = (
        SimpleNamespace(name="uses")
        if identifier is None
        else SimpleNamespace(id=identifier)
    )
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch(
            f"whub.commands.knowledge.{function_name}",
            return_value=returned,
        ) as operation,
    ):
        result = CliRunner().invoke(
            knowledge_command,
            ["add", *arguments, "--project", "local"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    operation.assert_called_once_with(loaded_manifest, "local", *expected_call)


@pytest.mark.parametrize(
    ("arguments", "target"),
    [
        (["con", "40"], "CON-040"),
        (["relation-type", "has_resource"], "has_resource"),
    ],
)
def test_rm_normalizes_category_target(
    arguments: list[str],
    target: str,
) -> None:
    loaded_manifest = manifest()
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch("whub.commands.knowledge.remove_knowledge") as operation,
    ):
        result = CliRunner().invoke(
            knowledge_command,
            ["rm", *arguments],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert result.output.strip() == f"removed {target}"
    operation.assert_called_once_with(loaded_manifest, "workspace-hub", target)


def test_reports_invalid_target_no_match_and_service_error() -> None:
    invalid_target = CliRunner().invoke(knowledge_command, ["rm", "con", "invalid"])
    assert invalid_target.exit_code != 0
    assert "expected a positive integer" in invalid_target.output

    with (
        patch("whub.commands.knowledge.get_manifest", return_value=manifest()),
        patch(
            "whub.commands.knowledge.load_project_knowledge",
            return_value=knowledge(),
        ),
    ):
        no_match = CliRunner().invoke(knowledge_command, ["query", "not-found"])
    assert no_match.exit_code != 0
    assert "no knowledge matches: not-found" in no_match.output

    with (
        patch("whub.commands.knowledge.get_manifest", return_value=manifest()),
        patch(
            "whub.commands.knowledge.load_project_knowledge",
            side_effect=ServiceError("knowledge unavailable"),
        ),
    ):
        service_error = CliRunner().invoke(knowledge_command, ["check"])
    assert service_error.exit_code != 0
    assert "knowledge unavailable" in service_error.output
