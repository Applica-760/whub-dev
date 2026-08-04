"""Agent-independent auth operations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import TypeVar

import yaml
from whub.models.agent.auth import (
    AgentAuth,
    CommandRule,
    EffectiveAuth,
    ExtensionTool,
    ExtensionToolCatalog,
    ExtensionToolId,
    LiteralValue,
    RegisteredProjectVariable,
    RegisteredTaskWorktreeVariable,
    VariableReference,
)
from whub.services.errors import ServiceError


class AuthError(ValueError):
    """Raised when Agent auths cannot be composed."""


class AgentAuthError(ValueError):
    """Raised when an Agent authorization asset cannot be loaded."""


class ExtensionToolError(ValueError):
    """Raised when a registered extension tool cannot be loaded."""


Item = TypeVar("Item")


@dataclass(frozen=True)
class ResolvedAgentAuth:
    """Effective authorization and tools for one Agent session."""

    auth: EffectiveAuth
    tools: tuple[ExtensionTool, ...]


def load_agent_auth(path: Path) -> AgentAuth:
    """Load and validate one Agent authorization asset."""
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise AgentAuthError(f"invalid agent auth asset: {path}") from error
    try:
        return AgentAuth.model_validate(data)
    except ValueError as error:
        raise AgentAuthError(f"invalid agent auth asset: {path}: {error}") from error


def load_extension_tool(directory: Path) -> ExtensionToolCatalog:
    """Load all registered extension tool assets in one directory."""
    try:
        data = [
            yaml.safe_load(path.read_text())
            for path in sorted(directory.glob("*.yaml"))
        ]
        return ExtensionToolCatalog.model_validate({"tools": data})
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as error:
        raise ExtensionToolError(
            f"invalid extension tool catalog: {directory}"
        ) from error


def resolve_agent_auth(auth_names: Sequence[str]) -> ResolvedAgentAuth:
    """Load and compose the base auth with named extension auths."""
    assets = _load_agent_assets(auth_names)
    auth = compose_auth(assets.base_auth, assets.extension_auths)
    tools = resolve_extension_tools(assets.extension_tool_catalog, auth.grants.extension_tools)
    return ResolvedAgentAuth(auth, tuple(tools))


def resolve_variables(
    definitions: Mapping[str, object],
    project: str,
    task_id: str,
    worktree: Path,
) -> dict[str, str]:
    """Resolve auth variables for one registered Project worktree."""
    values: dict[str, str] = {}
    for name, definition in definitions.items():
        if isinstance(definition, RegisteredProjectVariable):
            values[name] = project
        elif isinstance(definition, RegisteredTaskWorktreeVariable):
            available = {"project": project, "task": task_id, "path": str(worktree)}
            values.update(
                {f"{name}.{field}": available[field] for field in definition.fields}
            )
        else:
            raise ServiceError(f"unsupported Agent auth variable: {name}")
    return values


# --- Packaged Agent assets ---------------------------------------------------


@dataclass(frozen=True)
class _AgentAssets:
    """Packaged authorization assets for one Agent session."""

    base_auth: AgentAuth
    extension_auths: tuple[AgentAuth, ...]
    extension_tool_catalog: ExtensionToolCatalog


def _load_agent_assets(auth_names: Sequence[str]) -> _AgentAssets:
    if any(Path(name).name != name for name in auth_names):
        raise ServiceError("invalid Agent auth name")
    with as_file(files("whub").joinpath("assets")) as assets:
        return _AgentAssets(
            base_auth=load_agent_auth(assets / "roles" / "base.yaml"),
            extension_auths=tuple(
                load_agent_auth(assets / "roles" / name / "agent-auth.yaml")
                for name in auth_names
            ),
            extension_tool_catalog=load_extension_tool(assets / "extension_tools"),
        )


# --- Authorization composition and resolution -------------------------------


def compose_auth(base: AgentAuth, extensions: Sequence[AgentAuth]) -> EffectiveAuth:
    """Compose one base auth and zero or more extension auths."""
    if base.type != "base":
        raise AuthError("base auth must have type 'base'")
    if invalid := [auth.name for auth in extensions if auth.type != "extension"]:
        raise AuthError(f"extension auths must have type 'extension': {invalid}")

    auths = [base, *extensions]
    variables = dict(base.variables)
    for extension in extensions:
        for name, definition in extension.variables.items():
            existing = variables.get(name)
            if existing is not None and existing != definition:
                raise AuthError(f"conflicting variable definition: {name}")
            variables[name] = definition

    if any(auth.grants.network != base.grants.network for auth in extensions):
        raise AuthError("conflicting network grants")
    if any(auth.grants.approval != base.grants.approval for auth in extensions):
        raise AuthError("conflicting approval grants")

    return EffectiveAuth(
        variables=variables,
        grants={
            "commands": {
                "prefixes": _ordered_union(
                    rule for auth in auths for rule in auth.grants.commands.prefixes
                ),
                "exact": _ordered_union(
                    rule for auth in auths for rule in auth.grants.commands.exact
                ),
            },
            "filesystem": {
                "read": _ordered_union(
                    scope for auth in auths for scope in auth.grants.filesystem.read
                ),
                "write": _ordered_union(
                    scope for auth in auths for scope in auth.grants.filesystem.write
                ),
            },
            "network": base.grants.network,
            "extension_tools": _ordered_union(
                tool for auth in auths for tool in auth.grants.extension_tools
            ),
        },
    )


def allows_command(
    auth: EffectiveAuth,
    argv: Sequence[str],
    variables: Mapping[str, str],
) -> bool:
    """Return whether a resolved argv is allowed by an effective auth."""
    return any(
        _matches_rule(rule, argv, variables, prefix=True)
        for rule in auth.grants.commands.prefixes
    ) or any(
        _matches_rule(rule, argv, variables, prefix=False)
        for rule in auth.grants.commands.exact
    )


def resolve_extension_tools(
    catalog: ExtensionToolCatalog,
    ids: Sequence[ExtensionToolId],
) -> list[ExtensionTool]:
    """Resolve granted extension tool IDs from a Hub catalog."""
    by_id = {tool.id: tool for tool in catalog.tools}
    unknown_ids = sorted(set(ids) - by_id.keys())
    if unknown_ids:
        raise AuthError(f"unknown extension tools: {', '.join(unknown_ids)}")
    return [by_id[tool_id] for tool_id in ids]


def _ordered_union(items: Iterable[Item]) -> list[Item]:
    result: list[Item] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _matches_rule(
    rule: CommandRule,
    argv: Sequence[str],
    variables: Mapping[str, str],
    *,
    prefix: bool,
) -> bool:
    expected = [rule.executable]
    for token in rule.arguments:
        if isinstance(token, LiteralValue):
            expected.append(token.value)
        elif isinstance(token, VariableReference):
            value = variables.get(token.name)
            if value is None:
                return False
            expected.append(value)

    if len(argv) < len(expected) or argv[: len(expected)] != expected:
        return False
    return prefix or len(argv) == len(expected)
