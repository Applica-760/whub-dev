"""Remote file transfer operations."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from whub.core.context import WhubContext
from whub.core.remote import build_scp_command, remote_file_hash, remote_write_file
from whub.core.remote_files_meta import (
    get_remote_file_record, record_remote_file, remove_remote_file_record,
    resolve_remote_file_name, update_remote_file_hash,
)
from whub.core.target import TargetError, require_resource_type, resolve_resource_path
from whub.models import Manifest, RemoteResource
from whub.services.errors import ServiceError


def get_remote_file(
    manifest: Manifest, context: WhubContext, path: str
) -> tuple[str, Path, int]:
    try:
        project, resource, rel = resolve_resource_path(manifest, path)
        resource = require_resource_type(resource, RemoteResource, project.name)
    except TargetError as error:
        raise ServiceError(str(error)) from error
    if not rel:
        raise ServiceError(f"path must point to a file inside the resource: {path}")
    ref = f"{project.name}:{rel}"
    remote_files = context.remote_files_dir
    remote_files.mkdir(parents=True, exist_ok=True)
    local_name = resolve_remote_file_name(remote_files, ref, PurePosixPath(rel).name)
    destination = remote_files / local_name
    result = subprocess.run(build_scp_command(manifest.remote_host(resource), f"{manifest.remote_path(resource)}/{rel}", destination))
    if result.returncode == 0:
        record_remote_file(remote_files, local_name, ref, hashlib.sha256(destination.read_bytes()).hexdigest(), datetime.now(timezone.utc).isoformat())
    return project.name, destination, result.returncode


def put_remote_file(manifest: Manifest, context: WhubContext, local_name: str) -> tuple[str, str]:
    remote_files = context.remote_files_dir
    local_path = remote_files / local_name
    if not local_path.is_file():
        raise ServiceError(f"file not found in remote_files: {local_name}")
    record = get_remote_file_record(remote_files, local_name)
    if record is None:
        raise ServiceError(f"no fetch metadata for {local_name}; only files from whub get can be put")
    try:
        project, resource, rel = resolve_resource_path(manifest, record.ref)
        resource = require_resource_type(resource, RemoteResource, project.name)
    except TargetError as error:
        raise ServiceError(str(error)) from error
    remote_path = f"{manifest.remote_path(resource)}/{rel}"
    if remote_file_hash(manifest.remote_host(resource), remote_path) != record.sha256:
        raise ServiceError("remote file has changed or is unreadable since last fetch; run whub get again to take the latest version")
    result = remote_write_file(manifest.remote_host(resource), remote_path, local_path.read_text())
    if result.returncode != 0:
        raise ServiceError(f"remote write failed (exit {result.returncode}): {result.stderr.strip()}")
    update_remote_file_hash(remote_files, local_name, hashlib.sha256(local_path.read_bytes()).hexdigest(), datetime.now(timezone.utc).isoformat())
    return project.name, rel


def remove_remote_file(context: WhubContext, local_name: str) -> None:
    if PurePosixPath(local_name).name != local_name:
        raise ServiceError(f"LOCAL_NAME must be a file name: {local_name}")
    remote_files = context.remote_files_dir
    if get_remote_file_record(remote_files, local_name) is None:
        raise ServiceError(f"no fetch metadata for {local_name}; only files from whub get can be removed")
    local_path = remote_files / local_name
    if local_path.exists() and not local_path.is_file():
        raise ServiceError(f"not a file in remote_files: {local_name}")
    if local_path.exists():
        local_path.unlink()
    remove_remote_file_record(remote_files, local_name)
