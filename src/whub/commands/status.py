"""whub status — show health of all resources."""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.health import ResourceHealth, inspect_remote, inspect_symlink
from whub.models import Project, RemoteResource, SymlinkResource
from whub.remote import run_ssh_command
from whub.render import render_table
from whub.target import collect_targets, on_targets

@dataclass(frozen=True)
class _ResourceInfo:
    name: str
    resource_type: str
    health: ResourceHealth
    git_diff: str = "-"


def _fetch_local_info(r: SymlinkResource, project: Project) -> _ResourceInfo:
    health = inspect_symlink(r)
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
        name=project.name,
        resource_type=r.type,
        health=health,
        git_diff=git_diff,
    )

def _fetch_remote_info(r: RemoteResource, project: Project) -> _ResourceInfo:
    host = r._resolved_host
    health = inspect_remote(r)
    git_diff = "-"

    if health.state == "ok" and r.git is not None and host is not None:
        try:
            result = run_ssh_command(
                host,
                f"git -C {shlex.quote(r.path)} status --porcelain",
                batch_mode=True,
                connect_timeout=5,
                timeout=8,
            )
            if result.returncode == 0:
                lines = [l for l in result.stdout.splitlines() if l.strip()]
                git_diff = f"{len(lines)} files"
        except (OSError, subprocess.TimeoutExpired):
            pass

    return _ResourceInfo(
        name=project.name,
        resource_type=r.type,
        health=health,
        git_diff=git_diff,
    )


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show health of all resources."""
    m = get_manifest(ctx)
    targets = collect_targets(m)
    if not targets:
        click.echo("  (no resources)")
        return

    resource_infos = on_targets(targets, local=_fetch_local_info, remote=_fetch_remote_info,)
    rows = [
        (info.name, info.health.state, info.resource_type, info.git_diff)
        for info in resource_infos
    ]
    render_table(rows, right_align={3})

    if any(info.health.state != "ok" for info in resource_infos):
        raise click.exceptions.Exit(1)
