"""whub status — show status of all resources."""

from __future__ import annotations

import click

from whub.commands import get_manifest


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show status of all resources."""
    m = get_manifest(ctx)
    if not m.resources:
        click.echo("  (no resources)")
        return

    name_w = max(len(r.name) for r in m.resources)

    for r in m.resources:
        hub_path = m.resolve_path(r.path)
        if r.type == "symlink":
            mark = "ok" if hub_path.is_symlink() or hub_path.exists() else "missing"
        elif r.type == "mount":
            mark = "mounted" if hub_path.is_mount() else "not mounted"
        else:
            mark = "?"
        click.echo(f"  {r.name:<{name_w}}  {r.type:8s}  {mark}")
