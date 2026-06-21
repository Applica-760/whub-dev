"""whub status — show status of all resources."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.health import inspect_resource


@click.command()
@click.option("--check", "deep", is_flag=True, help="Check remote mount connectivity via SSH")
@click.pass_context
def status(ctx: click.Context, deep: bool) -> None:
    """Show status of all resources."""
    m = get_manifest(ctx)
    if not m.resources:
        click.echo("  (no resources)")
        return

    name_w = max(len(r.name) for r in m.resources)

    for r in m.resources:
        health = inspect_resource(r, m, deep=deep)
        click.echo(f"  {r.name:<{name_w}}  {r.type:8s}  {health.state}")
