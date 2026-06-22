"""whub doctor — check manifest and resource health."""
from __future__ import annotations
import click

@click.command()
def doctor() -> None:
    """Check manifest and resource health."""
    click.echo("doctor: not yet implemented")
