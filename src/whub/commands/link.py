"""whub link — create symlinks declared in the manifest."""

from __future__ import annotations

from pathlib import Path

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.services.link import create_links


@click.command()
@click.pass_context
def link(ctx: click.Context) -> None:
    """Create symlinks declared in the manifest."""
    workspace_root = current_context().workspace_root
    if Path.cwd() != workspace_root:
        raise click.ClickException("whub link must be run from the workspace root")
    for line in create_links(get_manifest(ctx), workspace_root):
        click.echo(line)
