"""Resource health inspection shared by commands."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never

from whub.models import Manifest, MountResource, Resource, SymlinkResource

HealthState = Literal[
    "ok",
    "missing",
    "source-missing",
    "broken",
    "wrong-target",
    "unexpected",
    "unmounted",
    "unreachable",
]


@dataclass(frozen=True)
class ResourceHealth:
    state: HealthState
    detail: str | None = None


def inspect_symlink(resource: SymlinkResource, manifest: Manifest) -> ResourceHealth:
    target = manifest.resolve_path(resource.path)
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


def inspect_mount(
    resource: MountResource,
    manifest: Manifest,
    *,
    deep: bool = False,
) -> ResourceHealth:
    target = manifest.resolve_path(resource.path)
    if not target.is_mount():
        return ResourceHealth("unmounted", str(target))
    if not deep:
        return ResourceHealth("ok")

    host = manifest.hosts[resource.host]
    command = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-i", str(Path(host.identity_file).expanduser()),
        "-p", str(host.port),
        f"{host.user}@{host.hostname}",
        f"test -d {shlex.quote(resource.remote_path)}",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired) as error:
        return ResourceHealth("unreachable", str(error))
    if result.returncode != 0:
        detail = result.stderr.strip() or f"ssh exited with status {result.returncode}"
        return ResourceHealth("unreachable", detail)
    return ResourceHealth("ok")


def inspect_resource(
    resource: Resource,
    manifest: Manifest,
    *,
    deep: bool = False,
) -> ResourceHealth:
    if isinstance(resource, SymlinkResource):
        return inspect_symlink(resource, manifest)
    if isinstance(resource, MountResource):
        return inspect_mount(resource, manifest, deep=deep)
    assert_never(resource)
