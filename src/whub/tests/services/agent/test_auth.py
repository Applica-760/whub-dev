import pytest
from pathlib import Path

from whub.models.agent.auth import (
    AgentAuth,
    CommandRule,
    ExtensionTool,
    RegisteredProjectVariable,
    RegisteredTaskWorktreeVariable,
)
from whub.services.agent.auth import (
    AgentAuthError,
    AuthError,
    allows_command,
    compose_auth,
    load_agent_auth,
    load_extension_tool,
    resolve_agent_auth,
    resolve_extension_tools,
)
from whub.services.errors import ServiceError


ASSETS = Path(__file__).parents[3] / "assets" / "roles"


def test_loads_agent_auth_assets() -> None:
    base = load_agent_auth(ASSETS / "base.yaml")
    implementer = load_agent_auth(ASSETS / "implementer" / "agent-auth.yaml")

    assert base.type == "base"
    assert isinstance(base.variables["project"], RegisteredProjectVariable)
    assert isinstance(base.grants.commands.prefixes[0], CommandRule)
    assert isinstance(base.grants.commands.exact[0], CommandRule)
    assert isinstance(
        implementer.variables["current_worktree"], RegisteredTaskWorktreeVariable
    )


def test_load_agent_auth_reports_invalid_assets(tmp_path: Path) -> None:
    data = (
        (ASSETS / "base.yaml")
        .read_text()
        .replace("read: []", "read: [unknown_scope]", 1)
    )
    target = tmp_path / "invalid-agent-auth.yaml"
    target.write_text(data)

    with pytest.raises(AgentAuthError):
        load_agent_auth(target)


def test_load_agent_auth_rejects_invalid_schema(tmp_path: Path) -> None:
    template = ASSETS / "templates" / "agent-auth.yaml"
    cases = (
        template.read_text().replace(
            "variables: {}",
            "variables:\n  project:\n    source: registered_project\n    fields: [project]",
        ),
        (ASSETS / "base.yaml")
        .read_text()
        .replace("read: []", "read: [current_worktree, current_worktree]", 1),
        (ASSETS / "base.yaml")
        .read_text()
        .replace("policy: deny_all", "outbound: []", 1),
    )
    target = tmp_path / "invalid-agent-auth.yaml"

    for data in cases:
        target.write_text(data)
        with pytest.raises(AgentAuthError):
            load_agent_auth(target)


def test_load_extension_tool_catalog() -> None:
    catalog = load_extension_tool(ASSETS.parent / "extension_tools")
    extension_tool = catalog.tools[0]

    assert isinstance(extension_tool, ExtensionTool)
    assert extension_tool.id == "codegraph"
    assert extension_tool.command == "codegraph"
    assert extension_tool.args == ["serve", "--mcp"]
    assert "explore" in extension_tool.tools

    auth = load_agent_auth(ASSETS / "base.yaml")
    resolved = resolve_extension_tools(catalog, auth.grants.extension_tools)
    assert [tool.id for tool in resolved] == ["codegraph"]
    with pytest.raises(AuthError, match="unknown extension tools"):
        resolve_extension_tools(catalog, ["unknown"])


def _auth(
    name: str,
    type: str,
    *,
    variables: dict | None = None,
    prefixes: list[dict] | None = None,
    exact: list[dict] | None = None,
    read: list[str] | None = None,
    write: list[str] | None = None,
    approval: dict[str, str] | None = None,
    extension_tools: list[str] | None = None,
) -> AgentAuth:
    return AgentAuth.model_validate(
        {
            "name": name,
            "type": type,
            "variables": variables or {},
            "grants": {
                "commands": {"prefixes": prefixes or [], "exact": exact or []},
                "filesystem": {"read": read or [], "write": write or []},
                "network": {"policy": "deny_all"},
                "approval": approval or {"policy": "request", "reviewer": "user"},
                "extension_tools": extension_tools or [],
            },
        }
    )


def test_compose_auth_unions_grants_and_matching_variables() -> None:
    base = _auth(
        "base",
        "base",
        variables={"project": {"source": "registered_project"}},
        exact=[{"executable": "date"}],
        read=[],
        extension_tools=["codegraph"],
    )
    extension = _auth(
        "implementer",
        "extension",
        variables={"project": {"source": "registered_project"}},
        prefixes=[
            {"executable": "whub", "arguments": ["worktree", "open", "$project"]}
        ],
        write=["current_worktree"],
        extension_tools=["codegraph"],
    )

    effective = compose_auth(base, [extension])

    assert list(effective.variables) == ["project"]
    assert effective.grants.filesystem.read == []
    assert effective.grants.filesystem.write == ["current_worktree"]
    assert effective.grants.extension_tools == ["codegraph"]
    assert allows_command(effective, ["date"], {})
    assert allows_command(
        effective,
        ["whub", "worktree", "open", "whub-dev", "28"],
        {"project": "whub-dev"},
    )


def test_resolve_agent_auth_loads_packaged_assets() -> None:
    resolved = resolve_agent_auth(("implementer",))

    assert resolved.auth.grants.extension_tools == ["codegraph"]
    assert [tool.id for tool in resolved.tools] == ["codegraph"]


def test_resolve_agent_auth_rejects_non_basename_extension_name() -> None:
    with pytest.raises(ServiceError, match="invalid Agent auth name"):
        resolve_agent_auth(("../implementer",))


def test_compose_auth_rejects_conflicting_variable_definitions() -> None:
    base = _auth(
        "base",
        "base",
        variables={"project": {"source": "registered_project"}},
    )
    extension = _auth(
        "implementer",
        "extension",
        variables={
            "project": {
                "source": "registered_task_worktree",
                "fields": ["project"],
            }
        },
    )

    with pytest.raises(AuthError, match="conflicting variable definition: project"):
        compose_auth(base, [extension])


def test_compose_auth_rejects_conflicting_approval_grants() -> None:
    base = _auth("base", "base")
    extension = _auth(
        "implementer",
        "extension",
        approval={"policy": "never", "reviewer": "user"},
    )

    with pytest.raises(AuthError, match="conflicting approval grants"):
        compose_auth(base, [extension])


def test_allows_command_distinguishes_prefix_and_exact_rules() -> None:
    base = _auth(
        "base",
        "base",
        variables={"project": {"source": "registered_project"}},
        prefixes=[
            {
                "executable": "whub",
                "arguments": ["worktree", "open", "$project"],
            }
        ],
        exact=[{"executable": "git", "arguments": ["diff"]}],
    )
    effective = compose_auth(base, [])

    assert allows_command(effective, ["git", "diff"], {})
    assert not allows_command(effective, ["git", "diff", "--stat"], {})
    assert allows_command(
        effective,
        ["whub", "worktree", "open", "whub-dev", "28"],
        {"project": "whub-dev"},
    )
    assert not allows_command(
        effective,
        ["whub", "worktree", "close", "whub-dev", "28"],
        {"project": "whub-dev"},
    )
    assert not allows_command(
        effective,
        ["whub", "worktree", "open", "whub-dev", "28"],
        {},
    )
