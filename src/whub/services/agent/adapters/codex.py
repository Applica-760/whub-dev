"""Render Codex project configuration from Agent authorization."""

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


class CodexAdapterError(ValueError):
    """Raised when an effective auth cannot be rendered for Codex."""


class CodexRuntimeRequirement(StrEnum):
    COMMAND_AUTHORIZATION = "command_authorization"
    FILESYSTEM_AUTHORIZATION = "filesystem_authorization"
    NETWORK_AUTHORIZATION = "network_authorization"


@dataclass(frozen=True)
class CodexRenderPlan:
    """Codex project files and the guards that the harness must provide."""

    files: Mapping[PurePosixPath, str]
    runtime_requirements: frozenset[CodexRuntimeRequirement]


def render(
    auth: EffectiveAuth,
    extension_tools: Sequence[ExtensionTool],
    variables: Mapping[str, str],
) -> CodexRenderPlan:
    """Render project-scoped Codex configuration without writing files."""
    tools = _resolve_extension_tools(auth, extension_tools)
    files: dict[PurePosixPath, str] = {}
    if auth.grants.commands.prefixes:
        files[PurePosixPath(".codex/rules/whub.rules")] = _render_rules(
            auth.grants.commands.prefixes,
            variables,
        )
    if tools:
        files[PurePosixPath(".codex/config.toml")] = _render_mcp_config(tools)
    return CodexRenderPlan(
        files=files,
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
        raise CodexAdapterError(f"unresolved extension tools: {', '.join(missing)}")
    return [by_id[tool_id] for tool_id in auth.grants.extension_tools]


def _render_rules(
    rules: Sequence[CommandRule],
    variables: Mapping[str, str],
) -> str:
    return "".join(
        "prefix_rule(\n"
        f"    pattern = {_starlark_list(_rule_arguments(rule, variables))},\n"
        '    decision = "allow",\n'
        ")\n"
        for rule in rules
    )


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
                raise CodexAdapterError(f"unresolved command variable: {token.name}")
            arguments.append(value)
    return arguments


def _render_mcp_config(tools: Sequence[ExtensionTool]) -> str:
    lines: list[str] = []
    for tool in tools:
        lines.extend(
            (
                f"[mcp_servers.{tool.id}]",
                f"command = {json.dumps(tool.command)}",
                f"args = {_toml_list(tool.args)}",
                f"enabled_tools = {_toml_list(_codex_tool_names(tool))}",
                "",
            )
        )
    return "\n".join(lines)


def _codex_tool_names(tool: ExtensionTool) -> list[str]:
    return [f"{tool.id}_{name}" for name in tool.tools]


def _runtime_requirements(
    auth: EffectiveAuth,
) -> frozenset[CodexRuntimeRequirement]:
    requirements: set[CodexRuntimeRequirement] = {
        CodexRuntimeRequirement.NETWORK_AUTHORIZATION,
    }
    if auth.grants.commands.prefixes or auth.grants.commands.exact:
        requirements.add(CodexRuntimeRequirement.COMMAND_AUTHORIZATION)
    if auth.grants.filesystem.read or auth.grants.filesystem.write:
        requirements.add(CodexRuntimeRequirement.FILESYSTEM_AUTHORIZATION)
    return frozenset(requirements)


def _starlark_list(values: Sequence[str]) -> str:
    return _toml_list(values)


def _toml_list(values: Sequence[str]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"
