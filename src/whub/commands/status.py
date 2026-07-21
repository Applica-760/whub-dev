"""whub status — show health of all resources."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.services.status import collect_resource_status
from whub.utils.render import render_table


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show health of all resources."""
    statuses = collect_resource_status(get_manifest(ctx))
    if not statuses:
        click.echo("  (no resources)")
        return

    render_table(
        [
            (item.project, item.state, item.type, item.mount, item.tmux, item.git)
            for item in statuses
        ],
        headers=("project", "state", "type", "mount", "tmux", "git"),
        right_align={5},
    )

    if any(item.state != "ok" or item.mount == "stale" for item in statuses):
        raise click.exceptions.Exit(1)
