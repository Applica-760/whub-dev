"""Agent-independent auth operations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TypeVar

from whub.models.agent.auth import (
    AgentAuth,
    CommandRule,
    EffectiveAuth,
    ExtensionTool,
    ExtensionToolCatalog,
    ExtensionToolId,
    LiteralValue,
    VariableReference,
)


class AuthError(ValueError):
    """Raised when Agent auths cannot be composed."""


Item = TypeVar("Item")


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
