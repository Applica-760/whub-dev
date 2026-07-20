"""`whub knowledge` CLIの読取り・更新境界テスト。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from whub.commands.knowledge import knowledge as knowledge_command
from whub.models import Manifest
from whub.services.errors import ServiceError
from whub.tests.helpers import knowledge, manifest, manifest_data


def test_check_defaults_to_workspace_hub() -> None:
    loaded_manifest = manifest()
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch(
            "whub.commands.knowledge.check_project_knowledge",
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
        "valid workspace-hub: 2 definitions, 1 relations, 1 policies, "
        "1 constraints, 1 exceptions"
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
    assert list(output["definitions"]) == ["project"]
    assert [entry["predicate"] for entry in output["relations"]] == ["manages"]
    assert set(output) == {"definitions", "relations"}
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
        "constraints": {
            "reject_unknown_fields": {
                "statement": "未知フィールドを拒否する"
            },
        },
    }
    missing_category = CliRunner().invoke(knowledge_command, ["ls"])
    assert missing_category.exit_code != 0
    assert "Missing argument" in missing_category.output


@pytest.mark.parametrize(
    ("arguments", "function_name", "expected_call"),
    [
        (
            [
                "def",
                "resource",
                "resource",
                "接続先",
                "--ref",
                "docs/ref.md",
            ],
            "add_definition",
            ("resource", "resource", "接続先", "docs/ref.md"),
        ),
        (
            [
                "rel",
                "def:whub",
                "uses",
                "def:project",
                "--cardinality",
                "0..*",
                "--ref",
                "docs/ref.md",
            ],
            "add_relation",
            ("def:whub", "uses", "def:project", "0..*", "docs/ref.md"),
        ),
        (
            ["pol", "use_cli", "CLIを使う", "--ref", "docs/ref.md"],
            "add_policy",
            ("use_cli", "CLIを使う", "docs/ref.md"),
        ),
        (
            [
                "con",
                "preserve_references",
                "参照を保つ",
                "--ref",
                "docs/ref.md",
            ],
            "add_constraint",
            ("preserve_references", "参照を保つ", "docs/ref.md"),
        ),
        (
            [
                "exc",
                "migration",
                "con:reject_unknown_fields",
                "移行中",
                "旧形式を許可する",
                "--ref",
                "docs/ref.md",
            ],
            "add_exception",
            (
                "migration",
                "con:reject_unknown_fields",
                "移行中",
                "旧形式を許可する",
                "docs/ref.md",
            ),
        ),
    ],
)
def test_add_dispatches_category_specific_arguments(
    arguments: list[str],
    function_name: str,
    expected_call: tuple[str, ...],
) -> None:
    loaded_manifest = manifest()
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch(
            f"whub.commands.knowledge.{function_name}",
        ) as operation,
    ):
        result = CliRunner().invoke(
            knowledge_command,
            ["add", *arguments, "--project", "local"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    operation.assert_called_once_with(loaded_manifest, "local", *expected_call)


def test_rm_uses_slug_and_relation_composite_key() -> None:
    loaded_manifest = manifest()
    with (
        patch("whub.commands.knowledge.get_manifest", return_value=loaded_manifest),
        patch("whub.commands.knowledge.remove_knowledge") as remove_entry,
        patch("whub.commands.knowledge.remove_relation") as remove_edge,
    ):
        entry_result = CliRunner().invoke(
            knowledge_command,
            ["rm", "con", "preserve_references"],
            catch_exceptions=False,
        )
        relation_result = CliRunner().invoke(
            knowledge_command,
            ["rm", "rel", "def:whub", "uses", "def:project"],
            catch_exceptions=False,
        )

    assert entry_result.exit_code == 0
    assert entry_result.output.strip() == "removed con:preserve_references"
    remove_entry.assert_called_once_with(
        loaded_manifest,
        "workspace-hub",
        "con:preserve_references",
    )
    assert relation_result.exit_code == 0
    remove_edge.assert_called_once_with(
        loaded_manifest,
        "workspace-hub",
        "def:whub",
        "uses",
        "def:project",
    )


def test_reports_invalid_target_no_match_and_service_error() -> None:
    invalid_target = CliRunner().invoke(
        knowledge_command,
        ["rm", "rel", "def:whub"],
    )
    assert invalid_target.exit_code != 0
    assert "requires SUBJECT PREDICATE OBJECT" in invalid_target.output

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
            "whub.commands.knowledge.check_project_knowledge",
            side_effect=ServiceError("knowledge unavailable"),
        ),
    ):
        service_error = CliRunner().invoke(knowledge_command, ["check"])
    assert service_error.exit_code != 0
    assert "knowledge unavailable" in service_error.output


def test_relation_type_category_is_not_available() -> None:
    runner = CliRunner()

    added = runner.invoke(
        knowledge_command,
        ["add", "relation-type", "uses", "definition"],
    )
    listed = runner.invoke(knowledge_command, ["ls", "relation-type"])
    removed = runner.invoke(
        knowledge_command,
        ["rm", "relation-type", "uses"],
    )

    assert added.exit_code != 0
    assert "No such command 'relation-type'" in added.output
    assert listed.exit_code != 0
    assert removed.exit_code != 0


def test_crud_roundtrip_in_temporary_project(tmp_path: Path) -> None:
    data = manifest_data()
    source = tmp_path / "project"
    source.mkdir()
    data["projects"][0]["resource"]["source"] = str(source)
    loaded_manifest = Manifest.model_validate(data)
    runner = CliRunner()

    with patch(
        "whub.commands.knowledge.get_manifest",
        return_value=loaded_manifest,
    ):
        for arguments in (
            ["init", "--project", "local"],
            [
                "add",
                "def",
                "alpha",
                "alpha",
                "最初の定義",
                "--project",
                "local",
            ],
            [
                "add",
                "def",
                "beta",
                "beta",
                "次の定義",
                "--project",
                "local",
            ],
            [
                "add",
                "rel",
                "def:alpha",
                "uses",
                "def:beta",
                "--project",
                "local",
            ],
        ):
            result = runner.invoke(
                knowledge_command,
                arguments,
                catch_exceptions=False,
            )
            assert result.exit_code == 0

        listed = runner.invoke(
            knowledge_command,
            ["ls", "def", "--project", "local"],
            catch_exceptions=False,
        )
        queried = runner.invoke(
            knowledge_command,
            ["query", "alpha", "--project", "local"],
            catch_exceptions=False,
        )
        checked = runner.invoke(
            knowledge_command,
            ["check", "--project", "local"],
            catch_exceptions=False,
        )

        assert list(yaml.safe_load(listed.output)["definitions"]) == [
            "alpha",
            "beta",
        ]
        query_output = yaml.safe_load(queried.output)
        assert list(query_output["definitions"]) == ["alpha"]
        assert query_output["relations"][0]["predicate"] == "uses"
        assert checked.output.startswith("valid local:")

        for arguments in (
            [
                "rm",
                "rel",
                "def:alpha",
                "uses",
                "def:beta",
                "--project",
                "local",
            ],
            ["rm", "def", "alpha", "--project", "local"],
            ["rm", "def", "beta", "--project", "local"],
        ):
            result = runner.invoke(
                knowledge_command,
                arguments,
                catch_exceptions=False,
            )
            assert result.exit_code == 0

    knowledge_path = source / "docs" / "knowledge.yaml"
    assert yaml.safe_load(knowledge_path.read_text()) == {
        "schema_version": 4,
        "definitions": {},
        "relations": [],
        "policies": {},
        "constraints": {},
        "exceptions": {},
    }
    assert not list(source.rglob("*.tmp"))
