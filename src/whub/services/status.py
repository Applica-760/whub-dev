"""Resource status collection shared by CLI and web adapters."""

from __future__ import annotations

import shlex
import subprocess
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from whub.core.health import inspect_aggregated_mount, inspect_symlink
from whub.core.remote import SSH_CONNECTION_FAILURE, run_ssh_command
from whub.core.target import TargetItem, collect_targets
from whub.core.tmux import session_name
from whub.models import (
    Host,
    Project,
    RemoteResource,
    ResourceStatus,
    StatusReport,
    SymlinkResource,
)
from whub.services.remote.mount import host_mountpoint, host_volume_name
from whub.services.worktree import collect_worktree_status
from whub.services.manifest import ResolvedManifest


def _fetch_local_info(
    resource: SymlinkResource,
    data: tuple[ResolvedManifest, Project],
) -> ResourceStatus:
    manifest, project = data
    health = inspect_symlink(resource, manifest.workspace_path(resource))
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
    manifest: ResolvedManifest,
    host: Host,
    items: list[tuple[RemoteResource, Project]],
) -> dict[int, tuple[str, str, str]] | None:
    script = "; ".join(
        _probe_line(index, manifest.remote_path(resource), session_name(project.name))
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
    manifest: ResolvedManifest,
    resource: RemoteResource,
    project: Project,
    probe: tuple[str, str, str] | None,
) -> ResourceStatus:
    mount = inspect_aggregated_mount(
        resource,
        host_mountpoint(resource.host),
        host_volume_name(resource.host),
        target=manifest.workspace_path(resource),
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
    manifest: ResolvedManifest,
    remotes: list[tuple[RemoteResource, Project]],
) -> dict[str, ResourceStatus]:
    by_host: dict[str, list[tuple[RemoteResource, Project]]] = defaultdict(list)
    for resource, project in remotes:
        by_host[resource.host].append((resource, project))

    infos: dict[str, ResourceStatus] = {}
    for items in by_host.values():
        probe = _probe_host(manifest, manifest.remote_host(items[0][0]), items)
        for index, (resource, project) in enumerate(items):
            entry = probe.get(index) if probe is not None else None
            infos[project.name] = _fetch_remote_info(
                manifest, resource, project, entry
            )
    return infos


def collect_resource_status(manifest: ResolvedManifest) -> list[ResourceStatus]:
    targets = [
        TargetItem(target.resource, (manifest, target.data))
        for target in collect_targets(manifest)
        if target.resource.status
    ]
    remotes = [
        (target.resource, target.data[1])
        for target in targets
        if isinstance(target.resource, RemoteResource)
    ]
    remote_infos = _collect_remote_infos(manifest, remotes)

    infos: list[ResourceStatus] = []
    for target in targets:
        resource = target.resource
        if isinstance(resource, SymlinkResource):
            infos.append(_fetch_local_info(resource, target.data))
        else:
            infos.append(remote_infos[target.data[1].name])
    return infos


def collect_status(manifest: ResolvedManifest, workspace_root: Path) -> StatusReport:
    """Collect resources and attach each worktree to its parent resource."""
    resources = collect_resource_status(manifest)
    grouped: dict[str, list] = {}
    invalid = []
    for worktree in collect_worktree_status(manifest, workspace_root):
        if worktree.parent_project is None:
            invalid.append(worktree)
        else:
            grouped.setdefault(worktree.parent_project, []).append(worktree)
    attached = tuple(
        replace(resource, worktrees=tuple(grouped.pop(resource.project, [])))
        for resource in resources
    )
    return StatusReport(attached, tuple([*invalid, *sum(grouped.values(), [])]))
