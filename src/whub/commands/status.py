"""whub status — show health of all resources."""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.health import ResourceHealth
from whub.models import Project, RemoteResource, SymlinkResource
from whub.remote import run_ssh_command
from whub.render import render_table
from whub.target import collect_targets, on_targets
from whub.health import inspect_symlink

@dataclass(frozen=True)
class _ResourceInfo:
    name: str
    resource_type: str
    health: ResourceHealth
    git_diff: str = "-"


def _fetch_symlink_info(r: SymlinkResource, project: Project) -> _ResourceInfo:
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

# 🚨エラーが発生したら失敗原因が伝わるInfoオブジェクトを返しているがこのフローは適切か？
def _fetch_remote_info(r: RemoteResource, project: Project) -> _ResourceInfo:
    host = r._resolved_host
    health: ResourceHealth
    git_diff = "-"
    if host is None:
        return _ResourceInfo(
            name=project.name,
            resource_type=r.type,
            health=ResourceHealth("unexpected", "remote host is unresolved"),
            git_diff=git_diff,
        )

    # このif elseは適切？　コマンド組み立てはここで直接持たせてもいいのかね
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
            name=project.name,
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

    # 🚨resource_infosの方が親切では？
    infos = on_targets(targets, local=_fetch_symlink_info, remote=_fetch_remote_info)
    rows = [
        (info.name, info.health.state, info.resource_type, info.git_diff)
        for info in infos
    ]
    render_table(rows, right_align={3})

    if any(info.health.state != "ok" for info in infos):
        raise click.exceptions.Exit(1)
