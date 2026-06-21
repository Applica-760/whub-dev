"""whub mount / unmount — sshfs-based remote directory mounting."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click

from whub.commands import get_manifest, host_names
from whub.health import inspect_resource
from whub.models import Manifest, MountResource

_SSHFS_OPTIONS = [
    "reconnect",
    "ServerAliveInterval=15",
    "ServerAliveCountMax=3",
]

_INSTALL_HINT = (
    "sshfs not found. Install via Homebrew:\n"
    "  brew install --cask fuse-t\n"
    "  brew install macos-fuse-t/cask/sshfs-fuse-t"
)


def _require_sshfs() -> str:
    path = shutil.which("sshfs")
    if not path:
        raise RuntimeError(_INSTALL_HINT)
    return path


def _mount_one(r: MountResource, m: Manifest) -> str:
    local = m.resolve_path(r.path)
    if inspect_resource(r, m).state == "ok":
        return "skip"

    local.mkdir(parents=True, exist_ok=True)

    host = m.hosts[r.host]
    remote = f"{host.user}@{host.hostname}:{r.remote_path}"
    identity = str(Path(host.identity_file).expanduser())

    cmd = [
        _require_sshfs(),
        remote,
        str(local),
        "-s",
        "-o", f"IdentityFile={identity}",
        "-o", f"port={host.port}",
    ]
    for opt in _SSHFS_OPTIONS:
        cmd.extend(["-o", opt])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"FAIL: {result.stderr.strip()}"
    health = inspect_resource(r, m)
    return "mount" if health.state == "ok" else f"FAIL: {health.state}"


def _unmount_one(r: MountResource, m: Manifest) -> str:
    local = m.resolve_path(r.path)
    if inspect_resource(r, m).state == "unmounted":
        return "skip"

    result = subprocess.run(["umount", str(local)], capture_output=True, text=True)
    if result.returncode != 0:
        return f"FAIL: {result.stderr.strip()}"
    health = inspect_resource(r, m)
    return "unmount" if health.state == "unmounted" else "FAIL: still mounted"


def _mount_all(
    m: Manifest, host_filter: str | None = None, include_all: bool = False,
) -> list[tuple[str, str]]:
    _require_sshfs()
    results = []
    for r in m.resources:
        if not isinstance(r, MountResource):
            continue
        if host_filter and r.host != host_filter:
            continue
        host = m.hosts[r.host]
        if not host_filter and not include_all and not host.auto_mount:
            continue
        status = _mount_one(r, m)
        results.append((r.name, status))
    return results


def _unmount_all(
    m: Manifest, host_filter: str | None = None,
) -> list[tuple[str, str]]:
    results = []
    for r in m.resources:
        if not isinstance(r, MountResource):
            continue
        if host_filter and r.host != host_filter:
            continue
        status = _unmount_one(r, m)
        results.append((r.name, status))
    return results


def _print_results(results: list[tuple[str, str]]) -> None:
    for name, status in results:
        click.echo(f"  {status:6s}  {name}")
    if not results:
        click.echo("  (no mount targets)")


@click.command()
@click.argument("host", required=False, shell_complete=host_names)
@click.option("--all", "include_all", is_flag=True, help="Include hosts with auto_mount=false")
@click.pass_context
def mount(ctx: click.Context, host: str | None, include_all: bool) -> None:
    """Mount remote directories via sshfs."""
    try:
        results = _mount_all(get_manifest(ctx), host_filter=host, include_all=include_all)
    except RuntimeError as e:
        raise click.ClickException(str(e))
    _print_results(results)


@click.command()
@click.argument("host", required=False, shell_complete=host_names)
@click.pass_context
def unmount(ctx: click.Context, host: str | None) -> None:
    """Unmount remote directories."""
    _print_results(_unmount_all(get_manifest(ctx), host_filter=host))
