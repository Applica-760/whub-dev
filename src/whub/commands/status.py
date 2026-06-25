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
from whub.target import on_targets
from whub.health import inspect_symlink

@dataclass(frozen=True)
class _ResourceInfo:
    name: str
    resource_type: str
    health: ResourceHealth
    git_diff: str = "-"


@dataclass(frozen=True)
class _StatusData:
    name: str
    manifest: Manifest


def _fetch_symlink_info(r: SymlinkResource, data: _StatusData) -> _ResourceInfo:
    m = data.manifest
    health = inspect_symlink(r, m)
    git_diff = "-"

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
                git_diff = f"{len(lines)} files"
        except (OSError, subprocess.TimeoutExpired):
            pass

    return _ResourceInfo(
        name=data.name,
        resource_type=r.type,
        health=health,
        git_diff=git_diff,
    )


def _fetch_remote_info(r: RemoteResource, data: _StatusData) -> _ResourceInfo:
    m = data.manifest
    host = m.hosts[r.host]
    health: ResourceHealth
    git_diff = "-"

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
            name=data.name,
            resource_type=r.type,
            health=ResourceHealth("unreachable", str(error)),
            git_diff=git_diff,
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
            git_diff = f"{len(lines)} files"

    return _ResourceInfo(
        name=data.name,
        resource_type=r.type,
        health=health,
        git_diff=git_diff,
    )


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show health of all resources."""
    m = get_manifest(ctx)
    targets = [
        (resource, _StatusData(name, m))
        for name, resource in m.project_resources()
    ]
    if not targets:
        click.echo("  (no resources)")
        return

    infos = on_targets(targets, local=_fetch_symlink_info, remote=_fetch_remote_info)
    rows = [
        (info.name, info.health.state, info.resource_type, info.git_diff)
        for info in infos
    ]
    render_table(rows, right_align={3})

    if any(info.health.state != "ok" for info in infos):
        raise click.exceptions.Exit(1)
