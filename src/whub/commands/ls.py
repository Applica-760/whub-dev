"""whub ls — list configured projects."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.utils.render import render_table


@click.command("ls")
@click.pass_context
def ls(ctx: click.Context) -> None:
    """List configured projects."""
    projects = get_manifest(ctx).projects
    if not projects:
        click.echo("  (no projects)")
        return

    render_table(
        [
            (
                project.name,
                project.resource.type if project.resource else "-",
                project.resource.workspace_path if project.resource else "-",
            )
            for project in projects
        ],
        headers=("project", "type", "workspace_path"),
    )
