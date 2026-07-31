import pytest

from whub.models.agent.auth import AgentAuth
from whub.services.agent.auth import AuthError, allows_command, compose_auth


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
        read=["hub_logical_tree"],
        extension_tools=["codegraph"],
    )
    extension = _auth(
        "implementer",
        "extension",
        variables={"project": {"source": "registered_project"}},
        prefixes=[
            {
                "executable": "wflow",
                "arguments": ["task", "--project", "$project", "check"],
            }
        ],
        write=["current_worktree"],
        extension_tools=["codegraph"],
    )

    effective = compose_auth(base, [extension])

    assert list(effective.variables) == ["project"]
    assert effective.grants.filesystem.read == ["hub_logical_tree"]
    assert effective.grants.filesystem.write == ["current_worktree"]
    assert effective.grants.extension_tools == ["codegraph"]
    assert allows_command(effective, ["date"], {})
    assert allows_command(
        effective,
        ["wflow", "task", "--project", "whub-dev", "check", "078"],
        {"project": "whub-dev"},
    )


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
                "executable": "wflow",
                "arguments": ["task", "--project", "$project", "check"],
            }
        ],
        exact=[{"executable": "git", "arguments": ["diff"]}],
    )
    effective = compose_auth(base, [])

    assert allows_command(effective, ["git", "diff"], {})
    assert not allows_command(effective, ["git", "diff", "--stat"], {})
    assert allows_command(
        effective,
        ["wflow", "task", "--project", "whub-dev", "check", "078"],
        {"project": "whub-dev"},
    )
    assert not allows_command(
        effective,
        ["wflow", "task", "--project", "whub-dev", "show", "078"],
        {"project": "whub-dev"},
    )
    assert not allows_command(
        effective,
        ["wflow", "task", "--project", "whub-dev", "check", "078"],
        {},
    )
