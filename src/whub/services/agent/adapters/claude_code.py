"""Render Claude Code project configuration from Agent authorization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import PurePosixPath

from whub.models.agent.auth import (
    CommandRule,
    EffectiveAuth,
    ExtensionTool,
    LiteralValue,
    VariableReference,
)


class ClaudeCodeAdapterError(ValueError):
    """Raised when an effective auth cannot be rendered for Claude Code."""


class ClaudeCodeRuntimeRequirement(StrEnum):
    COMMAND_AUTHORIZATION = "command_authorization"
    FILESYSTEM_AUTHORIZATION = "filesystem_authorization"
    NETWORK_AUTHORIZATION = "network_authorization"


@dataclass(frozen=True)
class ClaudeCodeRenderPlan:
    """Claude Code project files and guards that Agent must provide."""

    files: Mapping[PurePosixPath, str]
    runtime_requirements: frozenset[ClaudeCodeRuntimeRequirement]


def render(
    auth: EffectiveAuth,
    extension_tools: Sequence[ExtensionTool],
    variables: Mapping[str, str],
) -> ClaudeCodeRenderPlan:
    """Render project-scoped Claude Code configuration without writing files."""
    tools = _resolve_extension_tools(auth, extension_tools)
    policy = {
        "prefixes": [
            _rule_arguments(rule, variables) for rule in auth.grants.commands.prefixes
        ],
        "exact": [
            _rule_arguments(rule, variables) for rule in auth.grants.commands.exact
        ],
        "mcp_tools": [
            f"mcp__{tool.id}__{name}" for tool in tools for name in tool.tools
        ],
    }
    return ClaudeCodeRenderPlan(
        files={
            PurePosixPath(".claude/settings.json"): _render_settings(),
            PurePosixPath(".claude/hooks/whub_authorize.py"): _render_policy_hook(
                policy
            ),
            PurePosixPath(".mcp.json"): _render_mcp_config(tools),
        },
        runtime_requirements=_runtime_requirements(auth),
    )


def _resolve_extension_tools(
    auth: EffectiveAuth,
    extension_tools: Sequence[ExtensionTool],
) -> list[ExtensionTool]:
    by_id = {tool.id: tool for tool in extension_tools}
    missing = [
        tool_id for tool_id in auth.grants.extension_tools if tool_id not in by_id
    ]
    if missing:
        raise ClaudeCodeAdapterError(
            f"unresolved extension tools: {', '.join(missing)}"
        )
    return [by_id[tool_id] for tool_id in auth.grants.extension_tools]


def _rule_arguments(
    rule: CommandRule,
    variables: Mapping[str, str],
) -> list[str]:
    arguments = [rule.executable]
    for token in rule.arguments:
        if isinstance(token, LiteralValue):
            arguments.append(token.value)
        elif isinstance(token, VariableReference):
            value = variables.get(token.name)
            if value is None:
                raise ClaudeCodeAdapterError(
                    f"unresolved command variable: {token.name}"
                )
            arguments.append(value)
    return arguments


def _render_settings() -> str:
    hook = {
        "type": "command",
        "command": "python3",
        "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/whub_authorize.py"],
    }
    return _json(
        {
            "$schema": "https://json.schemastore.org/claude-code-settings.json",
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [hook]},
                    {"matcher": "mcp__.*", "hooks": [hook]},
                ]
            },
        }
    )


def _render_policy_hook(policy: Mapping[str, object]) -> str:
    return f'''#!/usr/bin/env python3
"""Generated Claude Code PreToolUse authorization hook."""

import json
import shlex
import sys

POLICY = {_json(policy).rstrip()}
SHELL_SYNTAX = set("|&;()<>\\n")


def deny(reason):
    json.dump(
        {{
            "hookSpecificOutput": {{
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}
        }},
        sys.stdout,
    )


def parse_argv(command):
    if any(character in command for character in SHELL_SYNTAX):
        return None
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return None


def command_allowed(argv):
    return any(argv[: len(rule)] == rule for rule in POLICY["prefixes"]) or any(
        argv == rule for rule in POLICY["exact"]
    )


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool_name = event.get("tool_name")
    if tool_name == "Bash":
        command = event.get("tool_input", {{}}).get("command")
        argv = parse_argv(command) if isinstance(command, str) else None
        if not argv or not command_allowed(argv):
            deny("command is not granted by Agent auth")
    elif isinstance(tool_name, str) and tool_name.startswith("mcp__"):
        if tool_name not in POLICY["mcp_tools"]:
            deny("MCP tool is not granted by Agent auth")


if __name__ == "__main__":
    main()
'''


def _render_mcp_config(tools: Sequence[ExtensionTool]) -> str:
    return _json(
        {
            "mcpServers": {
                tool.id: {
                    "type": tool.transport,
                    "command": tool.command,
                    "args": tool.args,
                }
                for tool in tools
            }
        }
    )


def _runtime_requirements(
    auth: EffectiveAuth,
) -> frozenset[ClaudeCodeRuntimeRequirement]:
    requirements: set[ClaudeCodeRuntimeRequirement] = {
        ClaudeCodeRuntimeRequirement.NETWORK_AUTHORIZATION,
    }
    if auth.grants.commands.prefixes or auth.grants.commands.exact:
        requirements.add(ClaudeCodeRuntimeRequirement.COMMAND_AUTHORIZATION)
    if auth.grants.filesystem.read or auth.grants.filesystem.write:
        requirements.add(ClaudeCodeRuntimeRequirement.FILESYSTEM_AUTHORIZATION)
    return frozenset(requirements)


def _json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
