"""whub mount / unmount — sshfs-based remote directory mounting."""

from __future__ import annotations
import subprocess
import click
from whub.commands import build_sshfs_command, get_manifest, host_names
from whub.health import inspect_resource
from whub.models import Manifest, MountResource


def _select_targets(
    m: Manifest,
    host: str | None = None,
    *,
    auto_only: bool = False,
) -> list[MountResource]:
    return [
        r for r in m.resources
        if isinstance(r, MountResource)
        and (host is None or r.host == host)
        and (not auto_only or m.hosts[r.host].auto_mount)
    ]


def _mount(m: Manifest, targets: list[MountResource]) -> list[tuple[str, str]]:
    results = []
    for r in targets:
        local = m.resolve_path(r.path)
        if inspect_resource(r, m).state == "ok":
            results.append((r.name, "skip"))
            continue

        local.mkdir(parents=True, exist_ok=True)
        cmd = build_sshfs_command(m.hosts[r.host], r.remote_path, local)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            status = f"FAIL: {result.stderr.strip()}"
        else:
            health = inspect_resource(r, m)
            status = "mount" if health.state == "ok" else f"FAIL: {health.state}"
        results.append((r.name, status))
    return results


def _unmount(m: Manifest, targets: list[MountResource]) -> list[tuple[str, str]]:
    results = []
    for r in targets:
        local = m.resolve_path(r.path)
        if inspect_resource(r, m).state == "unmounted":
            results.append((r.name, "skip"))
            continue

        result = subprocess.run(["umount", str(local)], capture_output=True, text=True)
        if result.returncode != 0:
            status = f"FAIL: {result.stderr.strip()}"
        else:
            health = inspect_resource(r, m)
            status = "unmount" if health.state == "unmounted" else "FAIL: still mounted"
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
    m = get_manifest(ctx)
    targets = _select_targets(m, host, auto_only=host is None and not include_all)
    _print_results(_mount(m, targets))


@click.command()
@click.argument("host", required=False, shell_complete=host_names)
@click.pass_context
def unmount(ctx: click.Context, host: str | None) -> None:
    """Unmount remote directories."""
    m = get_manifest(ctx)
    _print_results(_unmount(m, _select_targets(m, host)))
