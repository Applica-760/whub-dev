"""whub put — put a fetched file back to the remote resource."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.core.download_meta import get_download_record, update_download_hash
from whub.core.remote import remote_file_hash, remote_write_file
from whub.core.target import TargetError, require_resource_type, resolve_resource_path
from whub.models import RemoteResource


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
    update_download_hash(downloads, local_name, new_hash, datetime.now(timezone.utc).isoformat())
    click.echo(f"  put {project.name}: {local_name} -> {rel}")
