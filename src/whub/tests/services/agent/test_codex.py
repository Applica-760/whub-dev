from pathlib import PurePosixPath

import pytest

from whub.models.agent.auth import EffectiveAuth, ExtensionTool
from whub.services.agent.adapters.codex import (
    CodexAdapterError,
    CodexRuntimeRequirement,
    render,
)


def _auth() -> EffectiveAuth:
    return EffectiveAuth.model_validate(
        {
            "variables": {"project": {"source": "registered_project"}},
            "grants": {
                "commands": {
                    "prefixes": [
                        {
                            "executable": "wflow",
                            "arguments": [
                                "task",
                                "--project",
                                "$project",
                                "check",
                            ],
                        }
                    ],
                    "exact": [{"executable": "git", "arguments": ["diff"]}],
                },
                "filesystem": {
                    "read": ["hub_logical_tree"],
                    "write": ["current_worktree"],
                },
                "network": {"policy": "deny_all"},
                "extension_tools": ["codegraph"],
            },
        }
    )


def _codegraph() -> ExtensionTool:
    return ExtensionTool.model_validate(
        {
            "id": "codegraph",
            "protocol": "mcp",
            "transport": "stdio",
            "command": "codegraph",
            "args": ["serve", "--mcp"],
            "tools": ["explore", "node"],
        }
    )


def test_render_generates_project_rules_and_mcp_config() -> None:
    plan = render(_auth(), [_codegraph()], {"project": "whub-dev"})

    assert plan.files[PurePosixPath(".codex/rules/whub.rules")] == (
        'prefix_rule(\n    pattern = ["wflow", "task", "--project", "whub-dev", "check"],\n'
        '    decision = "allow",\n)\n'
    )
    assert plan.files[PurePosixPath(".codex/config.toml")] == (
        "[mcp_servers.codegraph]\n"
        'command = "codegraph"\n'
        'args = ["serve", "--mcp"]\n'
        'enabled_tools = ["codegraph_explore", "codegraph_node"]\n'
    )
    assert plan.runtime_requirements == frozenset(
        {
            CodexRuntimeRequirement.COMMAND_AUTHORIZATION,
            CodexRuntimeRequirement.FILESYSTEM_AUTHORIZATION,
            CodexRuntimeRequirement.NETWORK_AUTHORIZATION,
        }
    )


def test_render_rejects_unresolved_variables() -> None:
    with pytest.raises(CodexAdapterError, match="unresolved command variable: project"):
        render(_auth(), [_codegraph()], {})


def test_render_rejects_unresolved_extension_tools() -> None:
    with pytest.raises(
        CodexAdapterError, match="unresolved extension tools: codegraph"
    ):
        render(_auth(), [], {"project": "whub-dev"})
