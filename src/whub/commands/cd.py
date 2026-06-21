"""whub cd and shell integration."""

from __future__ import annotations

import os
import shlex
import sys

import click

from whub.commands import get_manifest, resource_names
from whub.models import MountResource, SymlinkResource

EXIT_SSH = 100

_SHELL_INIT = r"""
whub() {
    if [ "$1" = "cd" ] && [ -n "$2" ]; then
        local _out _rc
        _out="$(command whub "$@")"
        _rc=$?
        if [ $_rc -eq 0 ]; then
            builtin cd "$_out"
        elif [ $_rc -eq 100 ]; then
            command whub "$@"
        else
            echo "$_out" >&2
            return $_rc
        fi
    else
        command whub "$@"
    fi
}
source <(_WHUB_COMPLETE=zsh_source command whub)
"""


@click.command()
@click.argument("resource", shell_complete=resource_names)
@click.pass_context
def cd(ctx: click.Context, resource: str) -> None:
    """Jump to a resource (local cd or SSH)."""
    m = get_manifest(ctx)

    matched = next((r for r in m.resources if r.name == resource), None)
    if matched is None:
        raise click.ClickException(f"unknown resource: {resource}")

    if isinstance(matched, SymlinkResource):
        path = m.resolve_path(matched.path)
        if not path.exists():
            raise click.ClickException(f"symlink target does not exist: {path}")
        click.echo(str(path))

    elif isinstance(matched, MountResource):
        host = m.hosts[matched.host]
        identity = os.path.expanduser(host.identity_file)
        ssh_cmd = [
            "ssh", "-t",
            "-i", identity,
            "-p", str(host.port),
            f"{host.user}@{host.hostname}",
            f"cd {shlex.quote(matched.remote_path)} && exec $SHELL -l",
        ]
        if not sys.stdout.isatty():
            sys.exit(EXIT_SSH)
        try:
            os.execvp(ssh_cmd[0], ssh_cmd)
        except OSError as error:
            raise click.ClickException(f"failed to start ssh: {error}") from error


@click.command("shell-init")
@click.option("--shell", "shell_type", type=click.Choice(["zsh"]), default="zsh")
def shell_init(shell_type: str) -> None:
    """Emit zsh function and completion setup."""
    if shell_type == "zsh":
        click.echo(_SHELL_INIT.strip())
