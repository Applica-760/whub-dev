from pathlib import Path

import pytest
from pydantic import ValidationError

from whub.models.agent.auth import (
    AgentAuth,
    AgentAuthError,
    CommandRule,
    NetworkPolicy,
    RegisteredProjectVariable,
    RegisteredTaskWorktreeVariable,
    VariableReference,
    load_agent_auth,
)
from whub.models.agent.extension_tool import (
    ExtensionTool,
    load_extension_tool_catalog,
)
from whub.services.agent.auth import AuthError, resolve_extension_tools


ASSETS = Path(__file__).parents[2] / "assets" / "roles"


def test_loads_base_agent_auth() -> None:
    auth = load_agent_auth(ASSETS / "base.yaml")

    assert auth.type == "base"
    assert isinstance(auth.variables["project"], RegisteredProjectVariable)
    assert auth.grants.filesystem.read == ["hub_logical_tree"]
    assert auth.grants.filesystem.write == []
    assert auth.grants.extension_tools == ["codegraph"]
    assert isinstance(auth.grants.commands.prefixes[0], CommandRule)
    assert isinstance(auth.grants.commands.exact[0], CommandRule)
    assert auth.grants.network.policy is NetworkPolicy.DENY_ALL
    variable = auth.grants.commands.exact[-1].arguments[2]
    assert isinstance(variable, VariableReference)
    assert variable.name == "project"


def test_loads_implementer_agent_auth() -> None:
    auth = load_agent_auth(ASSETS / "implementer" / "agent-auth.yaml")

    assert auth.type == "extension"
    assert isinstance(
        auth.variables["current_worktree"], RegisteredTaskWorktreeVariable
    )
    assert auth.variables["current_worktree"].fields == ["project", "task", "path"]
    assert auth.grants.filesystem.read == []
    assert auth.grants.filesystem.write == ["current_worktree"]


def test_rejects_unknown_fields() -> None:
    data = {
        "name": "base",
        "type": "base",
        "variables": {},
        "grants": {
            "commands": {"prefixes": [], "exact": [], "templates": []},
            "filesystem": {"read": [], "write": []},
            "network": {"policy": "deny_all"},
            "extension_tools": [],
        },
        "unknown": True,
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AgentAuth.model_validate(data)


def test_rejects_registered_project_with_fields(tmp_path: Path) -> None:
    path = ASSETS / "templates" / "agent-auth.yaml"
    data = path.read_text().replace(
        "variables: {}",
        "variables:\n  project:\n    source: registered_project\n    fields: [project]",
    )
    target = tmp_path / "invalid-agent-auth.yaml"
    target.write_text(data)

    with pytest.raises(AgentAuthError, match="Extra inputs are not permitted"):
        load_agent_auth(target)


def test_rejects_unknown_filesystem_scope(tmp_path: Path) -> None:
    data = (
        (ASSETS / "base.yaml")
        .read_text()
        .replace("hub_logical_tree", "unknown_scope", 1)
    )
    target = tmp_path / "invalid-agent-auth.yaml"
    target.write_text(data)

    with pytest.raises(AgentAuthError):
        load_agent_auth(target)


def test_rejects_duplicate_filesystem_scope(tmp_path: Path) -> None:
    data = (
        (ASSETS / "base.yaml")
        .read_text()
        .replace(
            "read: [hub_logical_tree]", "read: [hub_logical_tree, hub_logical_tree]", 1
        )
    )
    target = tmp_path / "invalid-agent-auth.yaml"
    target.write_text(data)

    with pytest.raises(AgentAuthError, match="filesystem scopes must be unique"):
        load_agent_auth(target)


def test_rejects_network_configuration(tmp_path: Path) -> None:
    data = (
        (ASSETS / "base.yaml")
        .read_text()
        .replace("policy: deny_all", "outbound: []", 1)
    )
    target = tmp_path / "invalid-agent-auth.yaml"
    target.write_text(data)

    with pytest.raises(AgentAuthError, match="Extra inputs are not permitted"):
        load_agent_auth(target)


def test_loads_codegraph_extension_tool() -> None:
    catalog = load_extension_tool_catalog(ASSETS.parent / "extension_tools")
    extension_tool = catalog.tools[0]

    assert isinstance(extension_tool, ExtensionTool)
    assert extension_tool.id == "codegraph"
    assert "explore" in extension_tool.tools


def test_resolves_role_extension_tools() -> None:
    auth = load_agent_auth(ASSETS / "base.yaml")
    catalog = load_extension_tool_catalog(ASSETS.parent / "extension_tools")

    resolved = resolve_extension_tools(catalog, auth.grants.extension_tools)

    assert [tool.id for tool in resolved] == ["codegraph"]
    with pytest.raises(AuthError, match="unknown extension tools"):
        resolve_extension_tools(catalog, ["unknown"])
