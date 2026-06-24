"""whub status — show health of all resources."""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click

from whub.commands import get_manifest
from whub.health import ResourceHealth
from whub.models import Manifest, RemoteResource, SymlinkResource
from whub.remote import run_ssh_command
from whub.render import render_table


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


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show health of all resources."""
    m = get_manifest(ctx)
    resources = [r for r in m.all_resources if r.boot]
    if not resources:
        click.echo("  (no resources)")
        return

    infos = []
    for r in resources:
        if isinstance(r, SymlinkResource):
            infos.append(_fetch_symlink_info(r, m))
        else:
            infos.append(_fetch_remote_info(r, m))

    rows = [
        (info.name, info.health.state, info.resource_type, _format_git_column(info))
        for info in infos
    ]
    render_table(rows, right_align={3})

    if any(info.health.state != "ok" for info in infos):
        raise click.exceptions.Exit(1)
