"""Resource health inspection shared by commands."""
from __future__ import annotations
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never
from whub.models import Manifest, RemoteResource, SymlinkResource
from whub.remote import build_ssh_command

HealthState = Literal[
    "ok",
    "missing",
    "source-missing",
    "broken",
    "wrong-target",
    "unexpected",
    "unreachable",
]

@dataclass(frozen=True)
class ResourceHealth:
    state: HealthState
    detail: str | None = None

def inspect_symlink(resource: SymlinkResource, manifest: Manifest) -> ResourceHealth:
    target = manifest.resolve_path(resource.workspace_path)
    source = Path(resource.source).expanduser()

    if not source.exists():
        return ResourceHealth("source-missing", str(source))
    if target.is_symlink():
        try:
            resolved_target = target.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            return ResourceHealth("broken", str(error))
        if resolved_target == source.resolve():
            return ResourceHealth("ok")
        return ResourceHealth("wrong-target", str(resolved_target))
    if target.exists():
        return ResourceHealth("unexpected", str(target))
    return ResourceHealth("missing", str(target))

def inspect_remote(
    resource: RemoteResource,
    manifest: Manifest,
) -> ResourceHealth:
    host = manifest.hosts[resource.host]
    command = build_ssh_command(
        host,
        f"test -d {shlex.quote(resource.path)}",
        batch_mode=True,
        connect_timeout=5,
    )
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired) as error:
        return ResourceHealth("unreachable", str(error))
    if result.returncode == 255:
        detail = result.stderr.strip() or f"ssh exited with status {result.returncode}"
        return ResourceHealth("unreachable", detail)
    if result.returncode != 0:
        return ResourceHealth("missing", resource.path)
    return ResourceHealth("ok")

def inspect_resource(
    resource: SymlinkResource | RemoteResource,
    manifest: Manifest,
) -> ResourceHealth:
    if isinstance(resource, SymlinkResource):
        return inspect_symlink(resource, manifest)
    if isinstance(resource, RemoteResource):
        return inspect_remote(resource, manifest)
    assert_never(resource)
