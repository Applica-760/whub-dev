"""whub status — show health of all resources."""
from __future__ import annotations

import shlex
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.health import ResourceHealth, inspect_mount, inspect_symlink
from whub.models import Host, Project, RemoteResource, SymlinkResource
from whub.remote import run_ssh_command
from whub.render import render_table
from whub.target import collect_targets
from whub.tmux import session_name


@dataclass(frozen=True)
class _ResourceInfo:
    name: str
    resource_type: str
    health: ResourceHealth
    mount: str = "-"
    tmux: str = "-"
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


# ── Remote probe (1 SSH per host) ─────────────────────────────────
def _probe_line(index: int, path: str, session: str) -> str:
    p = shlex.quote(path)
    s = shlex.quote(session)
    return (
        f'echo "R{index}'
        f' $(test -d {p} && echo ok || echo missing)'
        f' $(git -C {p} status --porcelain 2>/dev/null | wc -l)'
        f' $(tmux has-session -t ={s} 2>/dev/null && echo on || echo -)"'
    )


def _parse_probe(stdout: str) -> dict[int, tuple[str, str, str]]:
    parsed: dict[int, tuple[str, str, str]] = {}
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) != 4 or not parts[0].startswith("R"):
            continue
        try:
            index = int(parts[0][1:])
        except ValueError:
            continue
        parsed[index] = (parts[1], parts[2], parts[3])
    return parsed


def _probe_host(
    host: Host,
    items: list[tuple[RemoteResource, Project]],
) -> dict[int, tuple[str, str, str]] | None:
    script = "; ".join(
        _probe_line(index, resource.path, session_name(project.name))
        for index, (resource, project) in enumerate(items)
    )
    try:
        result = run_ssh_command(
            host,
            script,
            batch_mode=True,
            connect_timeout=5,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 255:
        return None
    return _parse_probe(result.stdout)


def _fetch_remote_info(
    resource: RemoteResource,
    project: Project,
    probe: tuple[str, str, str] | None,
) -> _ResourceInfo:
    mount = inspect_mount(resource).state
    if probe is None:
        health = ResourceHealth("unreachable", str(resource._resolved_host.hostname))
        return _ResourceInfo(project.name, resource.type, health, mount=mount)

    exists, git_count, tmux = probe
    if exists != "ok":
        health = ResourceHealth("missing", resource.path)
        return _ResourceInfo(project.name, resource.type, health, mount=mount, tmux=tmux)

    git_diff = f"{git_count} files" if resource.git is not None else "-"
    return _ResourceInfo(
        project.name,
        resource.type,
        ResourceHealth("ok"),
        mount=mount,
        tmux=tmux,
        git_diff=git_diff,
    )


def _collect_remote_infos(
    remotes: list[tuple[RemoteResource, Project]],
) -> dict[str, _ResourceInfo]:
    by_host: dict[str, list[tuple[RemoteResource, Project]]] = defaultdict(list)
    for resource, project in remotes:
        by_host[resource.host].append((resource, project))

    infos: dict[str, _ResourceInfo] = {}
    for items in by_host.values():
        probe = _probe_host(items[0][0]._resolved_host, items)
        for index, (resource, project) in enumerate(items):
            entry = probe.get(index) if probe is not None else None
            infos[project.name] = _fetch_remote_info(resource, project, entry)
    return infos


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show health of all resources."""
    m = get_manifest(ctx)
    targets = [t for t in collect_targets(m) if t.resource.status]
    if not targets:
        click.echo("  (no resources)")
        return

    remotes = [
        (t.resource, t.data)
        for t in targets
        if isinstance(t.resource, RemoteResource)
    ]
    remote_infos = _collect_remote_infos(remotes)

    infos: list[_ResourceInfo] = []
    for target in targets:
        resource = target.resource
        if isinstance(resource, SymlinkResource):
            infos.append(_fetch_local_info(resource, target.data))
        else:
            infos.append(remote_infos[target.data.name])

    rows = [
        (info.name, info.health.state, info.resource_type, info.mount, info.tmux, info.git_diff)
        for info in infos
    ]
    render_table(
        rows,
        headers=("project", "state", "type", "mount", "tmux", "git"),
        right_align={5},
    )

    if any(info.health.state != "ok" or info.mount == "stale" for info in infos):
        raise click.exceptions.Exit(1)
