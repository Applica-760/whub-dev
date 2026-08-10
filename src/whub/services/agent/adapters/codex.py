"""Render Codex project configuration from Agent authorization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import PurePosixPath

from whub.models.agent.auth import (
    ApprovalPolicy,
    CommandRule,
    EffectiveAuth,
    ExtensionTool,
    LiteralValue,
    NetworkPolicy,
    VariableReference,
)


class CodexAdapterError(ValueError):
    """Raised when an effective auth cannot be rendered for Codex."""


def render(
    auth: EffectiveAuth,
    extension_tools: Sequence[ExtensionTool],
    variables: Mapping[str, str],
) -> dict[PurePosixPath, str]:
    """Render project-scoped Codex configuration without writing files."""
    tools = _resolve_extension_tools(auth, extension_tools)
    files: dict[PurePosixPath, str] = {
        PurePosixPath(".codex/config.toml"): _render_config(auth, tools)
    }
    if auth.grants.commands.prefixes:
        files[PurePosixPath(".codex/rules/whub.rules")] = _render_rules(
            auth.grants.commands.prefixes,
            variables,
        )
    return files


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
        f'    decision = "{rule.decision.value}",\n'
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


def _render_config(auth: EffectiveAuth, tools: Sequence[ExtensionTool]) -> str:
    lines = [
        f'sandbox_mode = "{_sandbox_mode(auth)}"',
        f'approval_policy = "{_approval_policy(auth)}"',
        f'approvals_reviewer = "{auth.grants.approval.reviewer.value}"',
        "",
        "[sandbox_workspace_write]",
        f"network_access = {_toml_bool(_network_access(auth))}",
        "exclude_tmpdir_env_var = false",
        "exclude_slash_tmp = false",
    ]
    for tool in tools:
        lines.extend(
            (
                "",
                f"[mcp_servers.{tool.id}]",
                f"command = {json.dumps(tool.command)}",
                f"args = {_toml_list(tool.args)}",
                f"enabled_tools = {_toml_list(_codex_tool_names(tool))}",
                "",
            )
        )
    return "\n".join(lines)


def _sandbox_mode(auth: EffectiveAuth) -> str:
    return "workspace-write" if auth.grants.filesystem.write else "read-only"


def _approval_policy(auth: EffectiveAuth) -> str:
    if auth.grants.approval.policy is ApprovalPolicy.REQUEST:
        return "on-request"
    if auth.grants.approval.policy is ApprovalPolicy.NEVER:
        return "never"
    raise CodexAdapterError(
        f"unsupported Codex approval policy: {auth.grants.approval.policy}"
    )


def _network_access(auth: EffectiveAuth) -> bool:
    if auth.grants.network.policy is NetworkPolicy.DENY_ALL:
        return False
    raise CodexAdapterError(
        f"unsupported Codex network policy: {auth.grants.network.policy}"
    )


def _codex_tool_names(tool: ExtensionTool) -> list[str]:
    return [f"{tool.id}_{name}" for name in tool.tools]


def _starlark_list(values: Sequence[str]) -> str:
    return _toml_list(values)


def _toml_list(values: Sequence[str]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"
