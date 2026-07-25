"""Shared host mount identifiers and paths."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from whub.core.context import current_context
from whub.core.health import ResourceHealth, inspect_mountpoint


def host_mount_id(host_name: str) -> str:
    """Return a safe single path component for a manifest host key."""
    return f"host-{quote(host_name, safe='')}"


def host_mountpoint(host_name: str) -> Path:
    """Return the runtime mountpoint for one host."""
    return current_context().directory / "runtime" / "mounts" / host_mount_id(host_name)


def host_volume_name(host_name: str) -> str:
    """Return the sshfs volume name for one host."""
    return f"whub-{host_mount_id(host_name)}"


def inspect_host_mount(host_name: str) -> ResourceHealth:
    """Inspect the shared mount managed for one manifest host."""
    return inspect_mountpoint(host_mountpoint(host_name), host_volume_name(host_name))
