"""whub mount / unmount — sshfs-based mounts for remote resources."""

from __future__ import annotations
from collections import defaultdict
from pathlib import Path, PurePosixPath
from posixpath import normpath
import shutil
import subprocess
import time
import contextlib
import click
from whub.commands import get_manifest
from whub.core.health import inspect_mount
from whub.core.mount_log import safe_option_names, write_mount_log
from whub.models import Manifest, Project, RemoteResource, project_names
from whub.core.remote import build_sshfs_command
from whub.services.mount import (
    host_mountpoint,
    host_volume_name,
    inspect_host_mount,
)
from whub.utils.render import render_table


def _select_targets(
    m: Manifest,
    name: str | None,
    *,
    auto_only: bool = False,
) -> list[tuple[Project, RemoteResource]]:
    if name is not None:
        # 名指しは明示された意図なのでmountフラグを無視する
        project = m.resolve_project(name)
        if project is None:
            raise click.ClickException(f"unknown project: {name}")
        if not isinstance(project.resource, RemoteResource):
            raise click.ClickException(f"not a remote resource: {name}")
        return [(project, project.resource)]
    return [
        (project, project.resource)
        for project in m.projects
        if isinstance(project.resource, RemoteResource)
        and (not auto_only or project.resource.mount)
    ]


def _mount_one(project: Project, resource: RemoteResource) -> str:
    mountpoint = resource._resolved_workspace_path
    host = resource._resolved_host
    health = inspect_mount(resource, project.name)
    write_mount_log(
        project=project.name,
        mountpoint=mountpoint,
        stage="precheck",
        result=health.state,
        detail=health.detail,
        recovery=health.recovery,
    )
    if health.state in ("ok", "slow"):
        return "skip"
    if health.state == "stale":
        return f"STALE: {health.detail}; recovery: {health.recovery}"
    if health.state == "unreadable":
        return f"UNREADABLE: {health.detail}; recovery: {health.recovery}"

    created_mountpoint = not mountpoint.exists()
    mountpoint.mkdir(parents=True, exist_ok=True)
    cmd = build_sshfs_command(
        host,
        resource.path,
        mountpoint,
        volname=f"whub-{project.name}",
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    options = safe_option_names(cmd)
    write_mount_log(
        project=project.name,
        mountpoint=mountpoint,
        stage="sshfs",
        result="ok" if result.returncode == 0 else "failed",
        # sshfs stderr may contain host, user, remote path, or identity path.
        detail="sshfs command failed" if result.returncode != 0 else None,
        recovery="check SSH connectivity and mount options"
        if result.returncode != 0
        else None,
        options=options,
    )
    if result.returncode != 0:
        if created_mountpoint:
            with contextlib.suppress(OSError):
                mountpoint.rmdir()
        return f"FAIL: {result.stderr.strip()}"
    # fuse-t on macOS: mount table lags ~0.2-0.4s behind sshfs exit.
    for _ in range(10):
        health = inspect_mount(resource, project.name)
        # slow=健全だが高遅延。unmountすると再mountフラッピングになるため成功扱い
        if health.state in ("ok", "slow"):
            write_mount_log(
                project=project.name,
                mountpoint=mountpoint,
                stage="post_mount_probe",
                result=health.state,
                detail=health.detail,
                options=options,
            )
            return "mount"
        if health.state == "unreadable":
            cleanup = _unmount_one(project, resource, force=True)
            if cleanup == "unmount" and created_mountpoint:
                with contextlib.suppress(OSError):
                    mountpoint.rmdir()
            write_mount_log(
                project=project.name,
                mountpoint=mountpoint,
                stage="cleanup",
                result=cleanup,
                detail=health.detail,
                recovery=health.recovery,
                options=options,
            )
            return (
                f"FAIL: mount unreadable: {health.detail}; cleanup={cleanup}; "
                f"recovery: {health.recovery}"
            )
        time.sleep(0.2)
    if health.state == "unmounted" and created_mountpoint:
        with contextlib.suppress(OSError):
            mountpoint.rmdir()
    write_mount_log(
        project=project.name,
        mountpoint=mountpoint,
        stage="post_mount_probe",
        result=health.state,
        detail=health.detail,
        recovery=health.recovery,
        options=options,
    )
    return f"FAIL: {health.state}: {health.detail}; recovery: {health.recovery}"


def _shared_source(resource: RemoteResource, mountpoint: Path) -> Path:
    mount_root = resource._resolved_host.mount_root
    if mount_root is None:
        raise ValueError("shared mount requires host.mount_root")
    relative = PurePosixPath(normpath(resource.path)).relative_to(mount_root)
    return mountpoint / Path(relative)


def _ensure_shared_links(
    targets: list[tuple[Project, RemoteResource]],
    mountpoint: Path,
) -> str | None:
    for _, resource in targets:
        target = resource._resolved_workspace_path
        source = _shared_source(resource, mountpoint)
        if target.is_symlink():
            linked = target.readlink()
            actual = linked if linked.is_absolute() else target.parent / linked
            if Path(normpath(str(actual))) == source:
                continue
            target.unlink()
        elif target.exists():
            return f"FAIL: workspace path is not a symlink: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
    return None


def _mount_host(
    host_name: str,
    targets: list[tuple[Project, RemoteResource]],
) -> str:
    resource = targets[0][1]
    host = resource._resolved_host
    mountpoint = host_mountpoint(host_name)
    health = inspect_host_mount(host_name)
    write_mount_log(
        project=host_name,
        mountpoint=mountpoint,
        stage="host_precheck",
        result=health.state,
        detail=health.detail,
        recovery=health.recovery,
    )
    if health.state in ("ok", "slow"):
        link_error = _ensure_shared_links(targets, mountpoint)
        return link_error or "skip"
    if health.state == "stale":
        return f"STALE: {health.detail}; recovery: {health.recovery}"
    if health.state == "unreadable":
        return f"UNREADABLE: {health.detail}; recovery: {health.recovery}"

    created_mountpoint = not mountpoint.exists()
    mountpoint.mkdir(parents=True, exist_ok=True)
    cmd = build_sshfs_command(
        host,
        host.mount_root or "",
        mountpoint,
        volname=host_volume_name(host_name),
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    options = safe_option_names(cmd)
    write_mount_log(
        project=host_name,
        mountpoint=mountpoint,
        stage="host_sshfs",
        result="ok" if result.returncode == 0 else "failed",
        detail="sshfs command failed" if result.returncode != 0 else None,
        recovery="check SSH connectivity and mount options"
        if result.returncode != 0
        else None,
        options=options,
    )
    if result.returncode != 0:
        if created_mountpoint:
            with contextlib.suppress(OSError):
                mountpoint.rmdir()
        return f"FAIL: {result.stderr.strip()}"
    for _ in range(10):
        health = inspect_host_mount(host_name)
        if health.state in ("ok", "slow"):
            link_error = _ensure_shared_links(targets, mountpoint)
            if link_error:
                return link_error
            write_mount_log(
                project=host_name,
                mountpoint=mountpoint,
                stage="host_post_mount_probe",
                result=health.state,
                detail=health.detail,
                options=options,
            )
            return "mount"
        if health.state == "unreadable":
            cleanup = _unmount_host(host_name, force=True)
            return (
                f"FAIL: mount unreadable: {health.detail}; cleanup={cleanup}; "
                f"recovery: {health.recovery}"
            )
        time.sleep(0.2)
    if health.state == "unmounted" and created_mountpoint:
        with contextlib.suppress(OSError):
            mountpoint.rmdir()
    return f"FAIL: {health.state}: {health.detail}; recovery: {health.recovery}"


def _unmount_host(host_name: str, force: bool) -> str:
    mountpoint = host_mountpoint(host_name)
    health = inspect_host_mount(host_name)
    if health.state == "unmounted":
        return "skip"
    if health.state == "stale" and not force:
        return "STALE: retry with --force"
    result = subprocess.run(
        ["umount", *(["-f"] if force else []), str(mountpoint)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and force:
        result = subprocess.run(
            ["diskutil", "unmount", "force", str(mountpoint)],
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        return f"FAIL: {result.stderr.strip()}"
    if inspect_host_mount(host_name).state != "unmounted":
        return "FAIL: still mounted"
    with contextlib.suppress(OSError):
        mountpoint.rmdir()
    return "unmount"


def _unmount_one(project: Project, resource: RemoteResource, force: bool) -> str:
    mountpoint = resource._resolved_workspace_path
    health = inspect_mount(resource, project.name)
    if health.state == "unmounted":
        return "skip"
    if health.state == "stale" and not force:
        return "STALE: retry with --force"

    cmd = ["umount", *(["-f"] if force else []), str(mountpoint)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and force:
        result = subprocess.run(
            ["diskutil", "unmount", "force", str(mountpoint)],
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        return f"FAIL: {result.stderr.strip()}"
    if inspect_mount(resource, project.name).state == "unmounted":
        return "unmount"
    return "FAIL: still mounted"


def _echo_results(results: list[tuple[str, str]]) -> None:
    ok_statuses = ("mount", "unmount", "skip")
    if not results:
        click.echo("  (no remote resources)")
        return
    render_table(
        [(status, name) for name, status in results],
        headers=("status", "project"),
    )
    if any(status not in ok_statuses for _, status in results):
        raise click.exceptions.Exit(1)


def _mount_targets(targets: list[tuple[Project, RemoteResource]]) -> None:
    results: list[tuple[str, str]] = []
    by_host: dict[str, list[tuple[Project, RemoteResource]]] = defaultdict(list)
    for project, resource in targets:
        if resource.mount and resource._resolved_host.mount_root is not None:
            by_host[resource.host].append((project, resource))
        else:
            result = _mount_one(project, resource)
            results.append((project.name, result))
    for host_name, host_targets in by_host.items():
        results.append((host_name, _mount_host(host_name, host_targets)))
    _echo_results(results)


def _unmount_targets(
    targets: list[tuple[Project, RemoteResource]],
    force: bool,
) -> None:
    results: list[tuple[str, str]] = []
    host_names: set[str] = set()
    for project, resource in targets:
        if resource.mount and resource._resolved_host.mount_root is not None:
            host_names.add(resource.host)
        else:
            result = _unmount_one(project, resource, force)
            results.append((project.name, result))
    for host_name in sorted(host_names):
        results.append((host_name, _unmount_host(host_name, force)))
    _echo_results(results)


@click.command()
@click.argument("project", required=False, shell_complete=project_names)
@click.option(
    "--all",
    "-a",
    "include_all",
    is_flag=True,
    help="Include resources with mount=false.",
)
@click.pass_context
def mount(ctx: click.Context, project: str | None, include_all: bool) -> None:
    """Mount remote resources via sshfs."""
    if shutil.which("sshfs") is None:
        raise click.ClickException("sshfs not found (brew install fuse-t sshfs-fuse-t)")
    m = get_manifest(ctx)
    targets = _select_targets(m, project, auto_only=not include_all)
    _mount_targets(targets)


@click.command()
@click.option("--force", is_flag=True, help="Force unmount (for stale mounts).")
@click.pass_context
def unmount(ctx: click.Context, force: bool) -> None:
    """Unmount all remote resources."""
    m = get_manifest(ctx)
    targets = _select_targets(m, None)
    _unmount_targets(targets, force)
