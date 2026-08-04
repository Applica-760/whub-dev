"""Remote file transfer commands."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.services.errors import ServiceError
from whub.services.remote.transfer import get_remote_file, put_remote_file, remove_remote_file


@click.command()
@click.argument("path", type=click.Path())
@click.pass_context
def get(ctx: click.Context, path: str) -> None:
    """Get a remote file by workspace-relative PATH or <project>:<path> ref."""
    try:
        project, destination, returncode = get_remote_file(
            get_manifest(ctx), current_context(), path
        )
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    if returncode:
        ctx.exit(returncode)
    click.echo(f"  get {project}: {destination}")


@click.command()
@click.argument("local_name")
@click.pass_context
def put(ctx: click.Context, local_name: str) -> None:
    """Put a fetched LOCAL_NAME back to the remote resource."""
    try:
        project, rel = put_remote_file(get_manifest(ctx), current_context(), local_name)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"  put {project}: {local_name} -> {rel}")


@click.command(name="rm")
@click.argument("local_name")
def rm(local_name: str) -> None:
    """Remove a fetched LOCAL_NAME and its metadata record."""
    try:
        remove_remote_file(current_context(), local_name)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"  rm {local_name}")
