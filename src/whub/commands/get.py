"""whub get — get a remote file into the workspace downloads directory."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import PurePosixPath

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.core.download_meta import record_download, resolve_local_name
from whub.core.remote import build_scp_command
from whub.core.target import (
    TargetError,
    require_resource_type,
    resolve_resource_path,
)
from whub.models import RemoteResource


@click.command()
@click.argument("path", type=click.Path())
@click.pass_context
def get(ctx: click.Context, path: str) -> None:
    """Get a remote file by workspace-relative PATH or <project>:<path> ref."""
    m = get_manifest(ctx)
    try:
        project, resource, rel = resolve_resource_path(m, path)
        resource = require_resource_type(resource, RemoteResource, project.name)
    except TargetError as error:
        raise click.ClickException(str(error)) from error
    if not rel:
        raise click.ClickException(
            f"path must point to a file inside the resource: {path}"
        )

    ref = f"{project.name}:{rel}"
    downloads = current_context().downloads_dir
    downloads.mkdir(parents=True, exist_ok=True)
    local_name = resolve_local_name(downloads, ref, PurePosixPath(rel).name)
    dest = downloads / local_name
    result = subprocess.run(
        build_scp_command(
            resource._resolved_host, f"{resource.remote_path}/{rel}", dest
        ),
    )
    if result.returncode != 0:
        ctx.exit(result.returncode)

    record_download(
        downloads,
        local_name,
        ref,
        hashlib.sha256(dest.read_bytes()).hexdigest(),
        datetime.now(timezone.utc).isoformat(),
    )
    click.echo(f"  get {project.name}: {dest}")
