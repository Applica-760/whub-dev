import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

import pytest

from whub.models.agent.auth import CommandDecision, EffectiveAuth, ExtensionTool
from whub.services.agent.adapters.claude_code import (
    ClaudeCodeAdapterError,
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
                            "executable": "whub",
                            "arguments": [
                                "worktree",
                                "open",
                                "$project",
                            ],
                        }
                    ],
                    "exact": [{"executable": "git", "arguments": ["diff"]}],
                },
                "filesystem": {
                    "read": [],
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

    settings = json.loads(plan[PurePosixPath(".claude/settings.json")])
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
    assert json.loads(plan[PurePosixPath(".mcp.json")]) == {
        "mcpServers": {
            "codegraph": {
                "type": "stdio",
                "command": "codegraph",
                "args": ["serve", "--mcp"],
            }
        }
    }
@pytest.mark.parametrize(
    ("event", "denied"),
    [
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "whub worktree open whub-dev 28"},
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
                    "command": "whub worktree open whub-dev 28 && rm -rf /"
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
    hook.write_text(plan[PurePosixPath(".claude/hooks/whub_authorize.py")])

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


def test_policy_hook_auto_allows_explicitly_allowed_commands(tmp_path: Path) -> None:
    auth = _auth()
    rule = auth.grants.commands.prefixes[0].model_copy(
        update={"decision": CommandDecision.ALLOW}
    )
    grants = auth.grants.model_copy(
        update={
            "commands": auth.grants.commands.model_copy(update={"prefixes": [rule]})
        }
    )
    hook = tmp_path / "whub_authorize.py"
    hook.write_text(
        render(
            auth.model_copy(update={"grants": grants}),
            [_codegraph()],
            {"project": "whub-dev"},
        )[PurePosixPath(".claude/hooks/whub_authorize.py")]
    )

    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "whub worktree open whub-dev 28"},
            }
        ),
        capture_output=True,
        check=True,
        text=True,
    )

    assert (
        json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    )


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
