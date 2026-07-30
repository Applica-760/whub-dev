from pathlib import Path

import pytest
from pydantic import ValidationError

from whub.models.agent_auth import (
    AgentAuth,
    AgentAuthError,
    CurrentWorktreeScope,
    ExactCommandRule,
    HubLogicalTreeScope,
    OptionArgument,
    PrefixCommandRule,
    RegisteredProjectVariable,
    RegisteredTaskWorktreeVariable,
    VariableReference,
    load_agent_auth,
)
from whub.models.extension_tool import (
    ExtensionTool,
    ExtensionToolError,
    load_extension_tool,
    load_extension_tool_catalog,
)


ASSETS = Path(__file__).parents[2] / "assets" / "roles"


def test_loads_base_agent_auth() -> None:
    auth = load_agent_auth(ASSETS / "base.yaml")

    assert auth.type == "base"
    assert isinstance(auth.variables["project"], RegisteredProjectVariable)
    assert isinstance(auth.grants.filesystem[0].scope, HubLogicalTreeScope)
    assert auth.grants.extension_tools == ["codegraph"]
    assert isinstance(auth.grants.commands.prefixes[0], PrefixCommandRule)
    assert isinstance(auth.grants.commands.exact[0], ExactCommandRule)
    option = auth.grants.commands.exact[-1].arguments[1]
    assert isinstance(option, OptionArgument)
    assert isinstance(option.option.value, VariableReference)
    assert option.option.value.name == "project"


def test_loads_implementer_agent_auth() -> None:
    auth = load_agent_auth(ASSETS / "implementer" / "agent-auth.yaml")

    assert auth.type == "extension"
    assert isinstance(
        auth.variables["current_worktree"], RegisteredTaskWorktreeVariable
    )
    assert auth.variables["current_worktree"].fields == ["project", "task", "path"]
    assert isinstance(auth.grants.filesystem[0].scope, CurrentWorktreeScope)


def test_rejects_unknown_fields() -> None:
    data = {
        "name": "base",
        "type": "base",
        "variables": {},
        "grants": {
            "commands": {"prefixes": [], "exact": [], "templates": []},
            "filesystem": [],
            "network": {"outbound": []},
            "extension_tools": [],
        },
        "unknown": True,
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AgentAuth.model_validate(data)


def test_rejects_registered_project_with_fields(tmp_path: Path) -> None:
    path = ASSETS / "templates" / "agent-auth.yaml"
    data = path.read_text().replace("variables: {}", "variables:\n  project:\n    source: registered_project\n    fields: [project]")
    target = tmp_path / "invalid-agent-auth.yaml"
    target.write_text(data)

    with pytest.raises(AgentAuthError, match="Extra inputs are not permitted"):
        load_agent_auth(target)


def test_rejects_unknown_filesystem_scope(tmp_path: Path) -> None:
    data = (ASSETS / "base.yaml").read_text().replace(
        "scope: hub_logical_tree", "scope: unknown_scope", 1
    )
    target = tmp_path / "invalid-agent-auth.yaml"
    target.write_text(data)

    with pytest.raises(AgentAuthError):
        load_agent_auth(target)


def test_loads_codegraph_extension_tool() -> None:
    extension_tool = load_extension_tool(
        ASSETS.parent / "extension_tools" / "codegraph.yaml"
    )

    assert isinstance(extension_tool, ExtensionTool)
    assert extension_tool.id == "codegraph"
    assert "codegraph_explore" in extension_tool.tools


def test_resolves_role_extension_tools() -> None:
    auth = load_agent_auth(ASSETS / "base.yaml")
    catalog = load_extension_tool_catalog(ASSETS.parent / "extension_tools")

    resolved = auth.resolve_extension_tools(catalog)

    assert [tool.id for tool in resolved] == ["codegraph"]
    with pytest.raises(ExtensionToolError, match="unknown extension tools"):
        catalog.resolve(["unknown"])
