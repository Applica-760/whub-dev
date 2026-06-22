"""whub cd and shell integration."""
from __future__ import annotations
import os
import shlex
import sys
import click
from whub.commands import build_ssh_command, get_manifest, resource_names
from whub.models import MountResource, SymlinkResource

EXIT_SSH = 100

_SHELL_INIT = r"""
whub() {
    if [ "$1" = "cd" ] && [ -n "$2" ]; then
        local target rc
        target="$(command whub "$@")"; rc=$?
        case $rc in
            0) builtin cd "$target" ;;
            100) command whub "$@" ;;
            *) return $rc ;;
        esac
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
        cmd = build_ssh_command(
            host,
            f"cd {shlex.quote(matched.remote_path)} && exec $SHELL -l",
            tty=True,
        )
        if not sys.stdout.isatty():
            sys.exit(EXIT_SSH)
        os.execvp("ssh", cmd)


@click.command("shell-init")
@click.option("--shell", "shell_type", type=click.Choice(["zsh"]), default="zsh")
def shell_init(shell_type: str) -> None:
    """Emit zsh function and completion setup."""
    if shell_type == "zsh":
        click.echo(_SHELL_INIT.strip())
