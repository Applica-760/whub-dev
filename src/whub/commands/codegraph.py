"""whub codegraph — initialize CodeGraph for configured Project resources."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.services.codegraph import initialize_codegraph


@click.command()
@click.pass_context
def codegraph(ctx: click.Context) -> None:
    """Initialize CodeGraph for enabled Project resources."""
    for line in initialize_codegraph(get_manifest(ctx)):
        click.echo(line)
