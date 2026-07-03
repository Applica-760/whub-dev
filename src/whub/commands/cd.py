"""whub cd and shell integration."""
from __future__ import annotations
import os
import shlex
import sys
import click
from whub.commands import get_manifest
from whub.models import RemoteResource, SymlinkResource, project_names
from whub.remote import build_ssh_command
from whub.tmux import build_shell_command, session_name
from whub.target import TargetItem, on_targets, resolve_project_resource

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


def _cd_local(resource: SymlinkResource, _data: tuple[str, bool]) -> None:
    path = resource._resolved_workspace_path
    if path is None:
        raise click.ClickException("workspace path is unresolved")
    if not path.exists():
        raise click.ClickException(f"symlink target does not exist: {path}")
    click.echo(str(path))


def _cd_remote(resource: RemoteResource, data: tuple[str, bool]) -> None:
    project, plain = data
    host = resource._resolved_host
    if host is None:
        raise click.ClickException(f"remote host is unresolved: {resource.host}")
    if plain:
        remote_command = f"cd {shlex.quote(resource.path)} && exec $SHELL -l"
    else:
        remote_command = build_shell_command(session_name(project), resource.path)
    cmd = build_ssh_command(host, remote_command, tty=True)
    if not sys.stdout.isatty():
        sys.exit(EXIT_SSH)
    os.execvp("ssh", cmd)


@click.command()
@click.argument("project", shell_complete=project_names)
@click.option("--plain", is_flag=True, help="Use a plain SSH shell instead of tmux.")
@click.pass_context
def cd(ctx: click.Context, project: str, plain: bool) -> None:
    """Jump to a project resource (local cd or SSH)."""
    m = get_manifest(ctx)
    resource = resolve_project_resource(m, project)
    on_targets(
        [TargetItem(resource, (project, plain))],
        local=_cd_local,
        remote=_cd_remote,
    )


@click.command("shell-init")
@click.option("--shell", "shell_type", type=click.Choice(["zsh"]), default="zsh")
def shell_init(shell_type: str) -> None:
    """Emit zsh function and completion setup."""
    if shell_type == "zsh":
        click.echo(_SHELL_INIT.strip())
