"""Shared helpers for CLI commands."""

from __future__ import annotations

import click

from whub.models import ManifestError
from whub.services.manifest import load_manifest


def project_names(ctx, param, incomplete: str) -> list[str]:
    """Complete project names without exposing manifest loading to adapters."""
    del ctx, param
    try:
        projects = load_manifest().projects
    except Exception:
        return []
    return [project.name for project in projects if project.name.startswith(incomplete)]


def get_manifest(ctx: click.Context):
    ctx.ensure_object(dict)
    if "manifest" not in ctx.obj:
        try:
            ctx.obj["manifest"] = load_manifest()
        except ManifestError as error:
            raise click.ClickException(str(error)) from error
    return ctx.obj["manifest"]
