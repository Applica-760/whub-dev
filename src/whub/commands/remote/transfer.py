"""Remote file transfer commands."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import PurePosixPath

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.core.download_meta import (
    get_download_record,
    record_download,
    resolve_local_name,
    update_download_hash,
)
from whub.core.remote import (
    build_scp_command,
    remote_file_hash,
    remote_write_file,
)
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


@click.command()
@click.argument("local_name")
@click.pass_context
def put(ctx: click.Context, local_name: str) -> None:
    """Put a fetched LOCAL_NAME back to the remote resource."""
    downloads = current_context().downloads_dir
    local_path = downloads / local_name
    if not local_path.is_file():
        raise click.ClickException(f"file not found in downloads: {local_name}")

    record = get_download_record(downloads, local_name)
    if record is None:
        raise click.ClickException(
            f"no fetch metadata for {local_name}; only files from whub get can be put"
        )

    m = get_manifest(ctx)
    try:
        project, resource, rel = resolve_resource_path(m, record.ref)
        resource = require_resource_type(resource, RemoteResource, project.name)
    except TargetError as error:
        raise click.ClickException(str(error)) from error

    remote_path = f"{resource.remote_path}/{rel}"
    current_hash = remote_file_hash(resource._resolved_host, remote_path)
    if current_hash != record.sha256:
        raise click.ClickException(
            "remote file has changed or is unreadable since last fetch; "
            "run whub get again to take the latest version"
        )

    content = local_path.read_text()
    result = remote_write_file(resource._resolved_host, remote_path, content)
    if result.returncode != 0:
        raise click.ClickException(
            f"remote write failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    new_hash = hashlib.sha256(local_path.read_bytes()).hexdigest()
    update_download_hash(
        downloads, local_name, new_hash, datetime.now(timezone.utc).isoformat()
    )
    click.echo(f"  put {project.name}: {local_name} -> {rel}")
