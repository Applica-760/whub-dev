"""Shared helpers for CLI commands."""

from __future__ import annotations

import click

from whub.models import ManifestError, load_manifest


def get_manifest(ctx: click.Context):
    ctx.ensure_object(dict)
    if "manifest" not in ctx.obj:
        try:
            ctx.obj["manifest"] = load_manifest()
        except ManifestError as error:
            raise click.ClickException(str(error)) from error
    return ctx.obj["manifest"]
