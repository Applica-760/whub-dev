"""Shared helpers for CLI commands."""

from __future__ import annotations

import click
from click.shell_completion import CompletionItem

from whub.manifest import load_manifest


def get_manifest(ctx: click.Context):
    return load_manifest(ctx.obj["manifest_path"])


def _load_names(key: str) -> list[str]:
    try:
        m = load_manifest()
    except Exception:
        return []
    if key == "resource":
        return [r.name for r in m.resources]
    if key == "host":
        return list(m.hosts or {})
    return []


def resource_names(ctx, param, incomplete: str) -> list[CompletionItem]:
    return [CompletionItem(n) for n in _load_names("resource") if n.startswith(incomplete)]


def host_names(ctx, param, incomplete: str) -> list[CompletionItem]:
    return [CompletionItem(n) for n in _load_names("host") if n.startswith(incomplete)]
