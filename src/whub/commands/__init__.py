"""Shared helpers for CLI commands."""

from __future__ import annotations

import click

from whub.models import load_manifest


def get_manifest(ctx: click.Context):
    ctx.ensure_object(dict)
    if "manifest" not in ctx.obj:
        ctx.obj["manifest"] = load_manifest()
    return ctx.obj["manifest"]
