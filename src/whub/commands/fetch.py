"""whub fetch — fetch a remote file into .whub/downloads/."""
from __future__ import annotations
import subprocess
from pathlib import Path, PurePosixPath
import click
from whub.commands import get_manifest
from whub.models import RemoteResource
from whub.remote import build_scp_command
from whub.target import resolve_resource_by_workspace_path

DOWNLOADS_DIR = Path(".whub/downloads")


@click.command()
@click.argument("path", type=click.Path())
@click.pass_context
def fetch(ctx: click.Context, path: str) -> None:
    """Fetch a remote file by its workspace-relative PATH."""
    m = get_manifest(ctx)
    project, resource, rel = resolve_resource_by_workspace_path(m, path)
    if not isinstance(resource, RemoteResource):
        raise click.ClickException(f"not a remote resource: {project.name}")
    if not rel:
        raise click.ClickException(f"path must point to a file inside the resource: {path}")

    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOADS_DIR / PurePosixPath(rel).name
    result = subprocess.run(
        build_scp_command(resource._resolved_host, f"{resource.path}/{rel}", dest),
    )
    if result.returncode != 0:
        ctx.exit(result.returncode)
    click.echo(f"  fetch {project.name}: {dest}")
