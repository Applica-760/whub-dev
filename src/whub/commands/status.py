"""whub status — show status of all resources."""
from __future__ import annotations
import click
from whub.commands import get_manifest
from whub.health import inspect_resource
from whub.models import SymlinkResource

@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show status of all resources."""
    m = get_manifest(ctx)
    resources = m.all_resources
    if not resources:
        click.echo("  (no resources)")
        return

    name_w = max(len(r.name) for r in resources)
    failed = False

    for r in resources:
        health = inspect_resource(r, m)
        resource_type = "symlink" if isinstance(r, SymlinkResource) else "remote"
        click.echo(f"  {r.name:<{name_w}}  {resource_type:8s}  {health.state}")
        failed |= health.state != "ok"

    if failed:
        raise click.exceptions.Exit(1)
