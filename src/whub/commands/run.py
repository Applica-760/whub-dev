"""Run a command in a remote resource."""
from __future__ import annotations
import subprocess
import click
from whub.commands import get_manifest
from whub.models import RemoteResource, resource_names
from whub.remote import build_remote_exec_command, build_ssh_command

@click.command(context_settings={
    "ignore_unknown_options": True,
    "allow_interspersed_args": False,
})
@click.option("--tty", is_flag=True, help="Allocate a terminal for interactive commands.")
@click.argument("resource", shell_complete=resource_names)
@click.argument("command", nargs=-1, type=click.UNPROCESSED, required=True)
@click.pass_context
def run(
    ctx: click.Context,
    tty: bool,
    resource: str,
    command: tuple[str, ...],
) -> None:
    """Run COMMAND in a remote RESOURCE."""
    manifest = get_manifest(ctx)
    matched = next(
        (item for item in manifest.all_resources if item.name == resource),
        None,
    )
    if matched is None:
        raise click.ClickException(f"unknown resource: {resource}")
    if not isinstance(matched, RemoteResource):
        raise click.ClickException(f"resource is not remote: {resource}")

    host = manifest.hosts[matched.host]
    remote_command = build_remote_exec_command(matched.path, command)
    ssh_command = build_ssh_command(host, remote_command, tty=tty)
    try:
        result = subprocess.run(ssh_command)
    except OSError as error:
        raise click.ClickException(str(error)) from error
    ctx.exit(result.returncode)
