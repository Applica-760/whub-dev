import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

import pytest

from whub.models.agent.auth import EffectiveAuth, ExtensionTool
from whub.services.agent.adapters.claude_code import (
    ClaudeCodeAdapterError,
    ClaudeCodeRuntimeRequirement,
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
            "tools": ["explore"],
        }
    )


def test_render_generates_settings_policy_hook_and_mcp_config() -> None:
    plan = render(_auth(), [_codegraph()], {"project": "whub-dev"})

    settings = json.loads(plan.files[PurePosixPath(".claude/settings.json")])
    assert settings["hooks"]["PreToolUse"] == [
        {
            "matcher": "Bash",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3",
                    "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/whub_authorize.py"],
                }
            ],
        },
        {
            "matcher": "mcp__.*",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3",
                    "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/whub_authorize.py"],
                }
            ],
        },
    ]
    assert json.loads(plan.files[PurePosixPath(".mcp.json")]) == {
        "mcpServers": {
            "codegraph": {
                "command": "codegraph",
                "args": ["serve", "--mcp"],
            }
        }
    }
    assert plan.runtime_requirements == frozenset(
        {
            ClaudeCodeRuntimeRequirement.COMMAND_AUTHORIZATION,
            ClaudeCodeRuntimeRequirement.FILESYSTEM_AUTHORIZATION,
            ClaudeCodeRuntimeRequirement.NETWORK_AUTHORIZATION,
        }
    )


@pytest.mark.parametrize(
    ("event", "denied"),
    [
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "wflow task --project whub-dev check 078"},
            },
            False,
        ),
        (
            {"tool_name": "Bash", "tool_input": {"command": "git diff"}},
            False,
        ),
        (
            {"tool_name": "Bash", "tool_input": {"command": "git diff --stat"}},
            True,
        ),
        (
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "wflow task --project whub-dev check 078 && rm -rf /"
                },
            },
            True,
        ),
        ({"tool_name": "mcp__codegraph__explore", "tool_input": {}}, False),
        ({"tool_name": "mcp__codegraph__search", "tool_input": {}}, True),
    ],
)
def test_policy_hook_allows_only_granted_commands_and_mcp_tools(
    tmp_path: Path,
    event: dict[str, object],
    *,
    denied: bool,
) -> None:
    plan = render(_auth(), [_codegraph()], {"project": "whub-dev"})
    hook = tmp_path / "whub_authorize.py"
    hook.write_text(plan.files[PurePosixPath(".claude/hooks/whub_authorize.py")])

    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(event),
        capture_output=True,
        check=True,
        text=True,
    )

    if denied:
        assert json.loads(result.stdout)["hookSpecificOutput"] == {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "command is not granted by Agent auth"
                if event["tool_name"] == "Bash"
                else "MCP tool is not granted by Agent auth"
            ),
        }
    else:
        assert result.stdout == ""


def test_render_rejects_unresolved_variables() -> None:
    with pytest.raises(
        ClaudeCodeAdapterError, match="unresolved command variable: project"
    ):
        render(_auth(), [_codegraph()], {})


def test_render_rejects_unresolved_extension_tools() -> None:
    with pytest.raises(
        ClaudeCodeAdapterError, match="unresolved extension tools: codegraph"
    ):
        render(_auth(), [], {"project": "whub-dev"})
