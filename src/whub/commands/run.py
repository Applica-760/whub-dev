"""whub run — one-shot command execution in a remote resource."""

from __future__ import annotations
import subprocess
import click
from whub.commands import get_manifest
from whub.models import RemoteResource, project_names
from whub.core.remote import build_remote_exec_command, build_ssh_command
from whub.core.target import (
    TargetError,
    require_resource_type,
    resolve_project_resource,
)


@click.command(
    context_settings={
        "ignore_unknown_options": True,
        "allow_interspersed_args": False,
    }
)
@click.option(
    "--tty", is_flag=True, help="Allocate a terminal for interactive commands."
)
@click.argument("project", shell_complete=project_names)
@click.argument("command", nargs=-1, type=click.UNPROCESSED, required=True)
@click.pass_context
def run(
    ctx: click.Context,
    tty: bool,
    project: str,
    command: tuple[str, ...],
) -> None:
    """Run COMMAND in a remote PROJECT (use `whub cd` for interactive sessions)."""
    m = get_manifest(ctx)
    try:
        resource = require_resource_type(
            resolve_project_resource(m, project),
            RemoteResource,
            project,
        )
    except TargetError as error:
        raise click.ClickException(str(error)) from error
    host = resource._resolved_host
    remote_command = build_remote_exec_command(resource.path, command)
    ssh_command = build_ssh_command(host, remote_command, tty=tty)
    result = subprocess.run(ssh_command)
    ctx.exit(result.returncode)
