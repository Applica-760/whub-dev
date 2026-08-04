"""whub cd and shell integration."""

from __future__ import annotations
import shlex
import subprocess
import sys
import click
from whub.commands import get_manifest
from whub.commands import project_names
from whub.models import RemoteResource, SymlinkResource
from whub.services.manifest import ResolvedManifest
from whub.core.remote import build_ssh_command
from whub.core.tmux import build_shell_command, session_name
from whub.core.target import (
    TargetError,
    TargetItem,
    on_targets,
    resolve_project_resource,
)

EXIT_SSH = 100

_TERMINAL_RECOVERY = "".join(
    (
        "\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1005l\x1b[?1006l",
        "\x1b[?1004l\x1b[?2004l",
        "\x1b[?1l\x1b>",
        "\x1b[?1049l",
    )
)

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


def _cd_local(resource: SymlinkResource, data: tuple[ResolvedManifest, str, bool]) -> None:
    path = data[0].workspace_path(resource)
    if not path.exists():
        raise click.ClickException(f"symlink target does not exist: {path}")
    click.echo(str(path))


def _cd_remote(resource: RemoteResource, data: tuple[ResolvedManifest, str, bool]) -> None:
    manifest, project, plain = data
    host = manifest.remote_host(resource)
    remote_path = manifest.remote_path(resource)
    if plain:
        remote_command = f"cd {shlex.quote(remote_path)} && exec $SHELL -l"
    else:
        remote_command = build_shell_command(
            session_name(project), remote_path
        )
    cmd = build_ssh_command(host, remote_command, tty=True)
    if not sys.stdout.isatty():
        sys.exit(EXIT_SSH)
    try:
        result = subprocess.run(cmd)
    finally:
        sys.stdout.write(_TERMINAL_RECOVERY)
        sys.stdout.flush()
    sys.exit(result.returncode)


@click.command()
@click.argument("project", shell_complete=project_names)
@click.option("--plain", is_flag=True, help="Use a plain SSH shell instead of tmux.")
@click.pass_context
def cd(ctx: click.Context, project: str, plain: bool) -> None:
    """Jump to a project resource (local cd or SSH)."""
    m = get_manifest(ctx)
    try:
        resource = resolve_project_resource(m, project)
    except TargetError as error:
        raise click.ClickException(str(error)) from error
    on_targets(
        [TargetItem(resource, (m, project, plain))],
        local=_cd_local,
        remote=_cd_remote,
    )


@click.command("shell-init")
@click.option("--shell", "shell_type", type=click.Choice(["zsh"]), default="zsh")
def shell_init(shell_type: str) -> None:
    """Emit zsh function and completion setup."""
    if shell_type == "zsh":
        click.echo(_SHELL_INIT.strip())
