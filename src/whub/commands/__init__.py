"""Shared helpers for CLI commands."""

from __future__ import annotations

import click
from click.shell_completion import CompletionItem

from whub.models import load_manifest


def get_manifest(ctx: click.Context):
    ctx.ensure_object(dict)
    if "manifest" not in ctx.obj:
        ctx.obj["manifest"] = load_manifest()
    return ctx.obj["manifest"]


def _load_names(key: str) -> list[str]:
    try:
        m = load_manifest()
    except Exception:
        return []
    if key == "resource":
        return [r.name for r in m.resources]
    if key == "host":
        return list(m.hosts)
    return []


def resource_names(ctx, param, incomplete: str) -> list[CompletionItem]:
    return [CompletionItem(n) for n in _load_names("resource") if n.startswith(incomplete)]


def host_names(ctx, param, incomplete: str) -> list[CompletionItem]:
    return [CompletionItem(n) for n in _load_names("host") if n.startswith(incomplete)]
