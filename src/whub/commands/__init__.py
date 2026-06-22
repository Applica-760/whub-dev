"""Shared helpers for CLI commands."""

from __future__ import annotations

from pathlib import Path

import click
from click.shell_completion import CompletionItem

from whub.models import Host, load_manifest


def ssh_target(host: Host) -> tuple[str, str, int]:
    target = f"{host.user}@{host.hostname}"
    identity = str(Path(host.identity_file).expanduser())
    return target, identity, host.port


def _option_args(options: tuple[str, ...]) -> list[str]:
    return [arg for option in options for arg in ("-o", option)]


def build_ssh_command(
    host: Host,
    remote_command: str,
    *,
    tty: bool = False,
    options: tuple[str, ...] = (),
) -> list[str]:
    """Build an SSH command."""
    target, identity, port = ssh_target(host)
    return [
        "ssh",
        *(["-t"] if tty else []),
        *_option_args(options),
        "-i", identity,
        "-p", str(port),
        target,
        remote_command,
    ]


def build_sshfs_command(
    host: Host,
    remote_path: str,
    mountpoint: Path,
) -> list[str]:
    """Build an sshfs command."""
    target, identity, port = ssh_target(host)
    return [
        "sshfs",
        f"{target}:{remote_path}",
        str(mountpoint),
        "-s",
        "-o", f"IdentityFile={identity}",
        "-o", f"port={port}",
        *_option_args((
            "reconnect",
            "ServerAliveInterval=15",
            "ServerAliveCountMax=3",
            "noappledouble",
            "noapplexattr",
            "defer_permissions",
        )),
    ]


def build_rsync_command(
    host: Host,
    local_src: str,
    remote_dest: str,
) -> list[str]:
    """Build an rsync command to sync local_src/ to remote host."""
    target, identity, port = ssh_target(host)
    return [
        "rsync", "-a",
        "-e", f"ssh -i {identity} -p {port}",
        f"{local_src}/",
        f"{target}:{remote_dest}/",
    ]


def get_manifest(ctx: click.Context):
    ctx.ensure_object(dict)
    if "manifest" not in ctx.obj:
        ctx.obj["manifest"] = load_manifest()
    return ctx.obj["manifest"]


def _load_names(key: str) -> list[str]:
    try:
        m = load_manifest()
    except Exception:
        return []
    if key == "resource":
        return [r.name for r in m.resources]
    if key == "host":
        return list(m.hosts)
    return []


def resource_names(ctx, param, incomplete: str) -> list[CompletionItem]:
    return [CompletionItem(n) for n in _load_names("resource") if n.startswith(incomplete)]


def host_names(ctx, param, incomplete: str) -> list[CompletionItem]:
    return [CompletionItem(n) for n in _load_names("host") if n.startswith(incomplete)]
