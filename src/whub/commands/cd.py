"""whub cd — jump to a resource (local cd or SSH)."""

from __future__ import annotations

import os
import shlex
import sys

import click

from whub.commands import get_manifest, resource_names

EXIT_SSH = 100


@click.command()
@click.argument("resource", shell_complete=resource_names)
@click.pass_context
def cd(ctx: click.Context, resource: str) -> None:
    """Jump to a resource (local cd or SSH)."""
    m = get_manifest(ctx)

    matched = next((r for r in m.resources if r.name == resource), None)
    if matched is None:
        raise click.ClickException(f"unknown resource: {resource}")

    if matched.type == "symlink":
        path = m.resolve_path(matched.path)
        if not path.exists():
            raise click.ClickException(f"symlink target does not exist: {path}")
        click.echo(str(path))

    elif matched.type == "mount":
        host = m.hosts[matched.host]
        identity = os.path.expanduser(host.identity_file)
        ssh_cmd = [
            "ssh", "-t",
            "-i", identity,
            "-p", str(host.port),
            f"{host.user}@{host.hostname}",
            f"cd {matched.remote_path} && exec $SHELL -l",
        ]
        click.echo(" ".join(shlex.quote(s) for s in ssh_cmd))
        sys.exit(EXIT_SSH)
