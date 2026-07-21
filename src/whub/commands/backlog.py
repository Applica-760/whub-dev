"""whub backlog — append a raw memo to a project's backlog."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.models import project_names
from whub.services.backlog import append_backlog
from whub.services.errors import ServiceError


@click.command()
@click.argument("text")
@click.option(
    "--project",
    default="workspace-hub",
    show_default=True,
    shell_complete=project_names,
)
@click.pass_context
def backlog(ctx: click.Context, text: str, project: str) -> None:
    """Append a raw memo to a project's backlog."""
    manifest = get_manifest(ctx)
    memo = text.strip()
    if not memo:
        raise click.UsageError("memo text is required")
    try:
        append_backlog(manifest, project, memo)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"  backlog {project}: {memo}")
