"""whub fetch — fetch a remote file into the whub downloads directory."""
from __future__ import annotations
import subprocess
from pathlib import PurePosixPath
import click
from whub.commands import get_manifest
from whub.models import RemoteResource
from whub.core.paths import downloads_dir
from whub.core.remote import build_scp_command
from whub.core.target import TargetError, require_resource_type, resolve_resource_by_workspace_path


@click.command()
@click.argument("path", type=click.Path())
@click.pass_context
def fetch(ctx: click.Context, path: str) -> None:
    """Fetch a remote file by its workspace-relative PATH."""
    m = get_manifest(ctx)
    try:
        project, resource, rel = resolve_resource_by_workspace_path(m, path)
        resource = require_resource_type(resource, RemoteResource, project.name)
    except TargetError as error:
        raise click.ClickException(str(error)) from error
    if not rel:
        raise click.ClickException(f"path must point to a file inside the resource: {path}")

    downloads = downloads_dir()
    downloads.mkdir(parents=True, exist_ok=True)
    dest = downloads / PurePosixPath(rel).name
    result = subprocess.run(
        build_scp_command(resource._resolved_host, f"{resource.path}/{rel}", dest),
    )
    if result.returncode != 0:
        ctx.exit(result.returncode)
    click.echo(f"  fetch {project.name}: {dest}")
