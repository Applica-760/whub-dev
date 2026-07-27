"""Resource status collection shared by CLI and web adapters."""

from __future__ import annotations

import shlex
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from whub.core.health import (
    HealthState,
    inspect_aggregated_mount,
    inspect_symlink,
)
from whub.core.remote import SSH_CONNECTION_FAILURE, run_ssh_command
from whub.core.target import collect_targets
from whub.core.tmux import session_name
from whub.models import Host, Manifest, Project, RemoteResource, SymlinkResource
from whub.services.remote.mount import host_mountpoint, host_volume_name


@dataclass(frozen=True)
class ResourceStatus:
    project: str
    state: HealthState
    type: str
    mount: str = "-"
    tmux: str = "-"
    git: str = "-"


def _fetch_local_info(
    resource: SymlinkResource,
    project: Project,
) -> ResourceStatus:
    health = inspect_symlink(resource)
    git = "-"

    if health.state == "ok" and resource.git is not None:
        source = Path(resource.source).expanduser()
        try:
            result = subprocess.run(
                ["git", "-C", str(source), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                lines = [line for line in result.stdout.splitlines() if line.strip()]
                git = f"{len(lines)} files"
            else:
                git = "failed"
        except (OSError, subprocess.TimeoutExpired):
            git = "failed"

    return ResourceStatus(project.name, health.state, resource.type, git=git)


def _probe_line(index: int, path: str, session: str) -> str:
    quoted_path = shlex.quote(path)
    quoted_session = shlex.quote(session)
    # git非リポジトリ・git未導入はカウント0と区別するため"?"を返す
    return (
        f'echo "R{index}'
        f" $(test -d {quoted_path} && echo ok || echo missing)"
        f" $(git -C {quoted_path} rev-parse --is-inside-work-tree >/dev/null 2>&1"
        f" && git -C {quoted_path} status --porcelain 2>/dev/null | wc -l || echo '?')"
        f' $(tmux has-session -t ={quoted_session} 2>/dev/null && echo on || echo -)"'
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
        _probe_line(index, resource.remote_path, session_name(project.name))
        for index, (resource, project) in enumerate(items)
    )
    try:
        result = run_ssh_command(
            host,
            script,
            batch_mode=True,
            connect_timeout=5,
            timeout=5 + 8 * len(items),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == SSH_CONNECTION_FAILURE:
        return None
    return _parse_probe(result.stdout)


def _fetch_remote_info(
    resource: RemoteResource,
    project: Project,
    probe: tuple[str, str, str] | None,
) -> ResourceStatus:
    mount = inspect_aggregated_mount(
        resource,
        host_mountpoint(resource.host),
        host_volume_name(resource.host),
    ).state
    if probe is None:
        return ResourceStatus(project.name, "unreachable", resource.type, mount=mount)

    exists, git_count, tmux = probe
    if exists != "ok":
        return ResourceStatus(
            project.name,
            "missing",
            resource.type,
            mount=mount,
            tmux=tmux,
        )

    if resource.git is None:
        git = "-"
    elif git_count == "?":
        git = "failed"
    else:
        git = f"{git_count} files"
    return ResourceStatus(project.name, "ok", resource.type, mount, tmux, git)


def _collect_remote_infos(
    remotes: list[tuple[RemoteResource, Project]],
) -> dict[str, ResourceStatus]:
    by_host: dict[str, list[tuple[RemoteResource, Project]]] = defaultdict(list)
    for resource, project in remotes:
        by_host[resource.host].append((resource, project))

    infos: dict[str, ResourceStatus] = {}
    for items in by_host.values():
        probe = _probe_host(items[0][0]._resolved_host, items)
        for index, (resource, project) in enumerate(items):
            entry = probe.get(index) if probe is not None else None
            infos[project.name] = _fetch_remote_info(resource, project, entry)
    return infos


def collect_resource_status(manifest: Manifest) -> list[ResourceStatus]:
    targets = [target for target in collect_targets(manifest) if target.resource.status]
    remotes = [
        (target.resource, target.data)
        for target in targets
        if isinstance(target.resource, RemoteResource)
    ]
    remote_infos = _collect_remote_infos(remotes)

    infos: list[ResourceStatus] = []
    for target in targets:
        resource = target.resource
        if isinstance(resource, SymlinkResource):
            infos.append(_fetch_local_info(resource, target.data))
        else:
            infos.append(remote_infos[target.data.name])
    return infos
