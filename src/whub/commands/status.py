"""whub status — show status of all resources."""
from __future__ import annotations

import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import click

from whub.commands import get_manifest
from whub.health import ResourceHealth
from whub.models import Manifest, RemoteResource, SymlinkResource
from whub.models.manifest import resource_names
from whub.models.state import PRIORITIES, ResourceState, load_state, save_state
from whub.remote import run_ssh_command


@dataclass(frozen=True)
class _ResourceInfo:
    name: str
    resource_type: str
    health: ResourceHealth
    git_diff_count: int | None


def _fetch_symlink_info(r: SymlinkResource, m: Manifest) -> _ResourceInfo:
    from whub.health import inspect_symlink

    health = inspect_symlink(r, m)
    git_diff: int | None = None

    if health.state == "ok" and r.git is not None:
        source = Path(r.source).expanduser()
        try:
            result = subprocess.run(
                ["git", "-C", str(source), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                lines = [l for l in result.stdout.splitlines() if l.strip()]
                git_diff = len(lines)
        except (OSError, subprocess.TimeoutExpired):
            pass

    return _ResourceInfo(
        name=r.name,
        resource_type="symlink",
        health=health,
        git_diff_count=git_diff,
    )


def _fetch_remote_info(r: RemoteResource, m: Manifest) -> _ResourceInfo:
    host = m.hosts[r.host]
    health: ResourceHealth
    git_diff: int | None = None

    if r.git is not None:
        cmd = (
            f"test -d {shlex.quote(r.path)}"
            f" && git -C {shlex.quote(r.path)} status --porcelain"
        )
    else:
        cmd = f"test -d {shlex.quote(r.path)}"

    try:
        result = run_ssh_command(
            host, cmd, batch_mode=True, connect_timeout=5, timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return _ResourceInfo(
            name=r.name,
            resource_type="remote",
            health=ResourceHealth("unreachable", str(error)),
            git_diff_count=None,
        )

    if result.returncode == 255:
        detail = result.stderr.strip() or f"ssh exited with status {result.returncode}"
        health = ResourceHealth("unreachable", detail)
    elif result.returncode != 0:
        health = ResourceHealth("missing", r.path)
    else:
        health = ResourceHealth("ok")
        if r.git is not None:
            lines = [l for l in result.stdout.splitlines() if l.strip()]
            git_diff = len(lines)

    return _ResourceInfo(
        name=r.name,
        resource_type="remote",
        health=health,
        git_diff_count=git_diff,
    )


def _format_git_column(info: _ResourceInfo) -> str:
    if info.git_diff_count is None:
        return "-"
    return f"{info.git_diff_count} files"


def _update_state(m: Manifest, resource: str, edit: str | None, priority: str | None) -> None:
    names = [r.name for r in m.all_resources]
    if resource not in names:
        raise click.UsageError(f"unknown resource: {resource}")
    state = load_state()
    rs = state.resources.get(resource, ResourceState())
    if edit is not None:
        rs = rs.model_copy(update={"status": edit})
    if priority is not None:
        rs = rs.model_copy(update={"priority": priority})
    state.resources[resource] = rs
    save_state(state)
    click.echo(f"  {rs.priority_icon} {resource}: {rs.status or ''}")


def _show_status(m: Manifest) -> None:
    resources = [r for r in m.all_resources if r.boot]
    if not resources:
        click.echo("  (no resources)")
        return

    infos: dict[str, _ResourceInfo] = {}

    for r in resources:
        if isinstance(r, SymlinkResource):
            infos[r.name] = _fetch_symlink_info(r, m)

    remotes = [r for r in resources if isinstance(r, RemoteResource)]
    if remotes:
        with ThreadPoolExecutor() as pool:
            futures = {
                pool.submit(_fetch_remote_info, r, m): r.name for r in remotes
            }
            for future in as_completed(futures):
                info = future.result()
                infos[info.name] = info

    state = load_state()
    all_infos = [infos[r.name] for r in resources]

    name_w = max(len(i.name) for i in all_infos)
    health_w = max(len(i.health.state) for i in all_infos)
    failed = False

    for info in all_infos:
        rs = state.resources.get(info.name, ResourceState())
        git_col = _format_git_column(info)
        click.echo(
            f"  {rs.priority_icon} {info.name:<{name_w}}"
            f"  {info.health.state:<{health_w}s}  {info.resource_type:8s}"
            f"  {git_col:>8s}  {rs.status or ''}"
        )
        failed |= info.health.state != "ok"

    if failed:
        raise click.exceptions.Exit(1)


@click.command()
@click.argument("resource", required=False, shell_complete=resource_names)
@click.option("-e", "--edit", metavar="TEXT", help="Set status text")
@click.option("-p", "--priority", type=click.Choice(PRIORITIES), help="Set priority")
@click.pass_context
def status(
    ctx: click.Context,
    resource: str | None,
    edit: str | None,
    priority: str | None,
) -> None:
    """Show status of all resources, or update a resource's state."""
    m = get_manifest(ctx)
    if edit is not None or priority is not None:
        if resource is None:
            raise click.UsageError("resource name required with -e or -p")
        _update_state(m, resource, edit, priority)
    else:
        _show_status(m)
