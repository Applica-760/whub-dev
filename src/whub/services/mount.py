"""sshfs mount orchestration shared by CLI and other adapters."""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from posixpath import normpath
from urllib.parse import quote

from whub.core.context import current_context
from whub.core.health import (
    ResourceHealth,
    aggregated_link_source,
    inspect_mountpoint,
)
from whub.core.mount_log import safe_option_names, write_mount_log
from whub.core.remote import build_sshfs_command
from whub.models import Manifest, Project, RemoteResource
from whub.services.errors import ServiceError

_OK_STATUSES = ("mount", "unmount", "skip")


@dataclass(frozen=True)
class MountResult:
    """One rendered mount/unmount outcome for a shared host."""

    name: str
    status: str

    @property
    def ok(self) -> bool:
        return self.status in _OK_STATUSES


def host_mount_id(host_name: str) -> str:
    """Return a safe single path component for a manifest host key."""
    return f"host-{quote(host_name, safe='')}"


def host_mountpoint(host_name: str) -> Path:
    """Return the runtime mountpoint for one host."""
    return current_context().directory / "runtime" / "mounts" / host_mount_id(host_name)


def host_volume_name(host_name: str) -> str:
    """Return the sshfs volume name for one host."""
    return f"whub-{host_mount_id(host_name)}"


def inspect_host_mount(host_name: str) -> ResourceHealth:
    """Inspect the shared mount managed for one manifest host."""
    return inspect_mountpoint(host_mountpoint(host_name), host_volume_name(host_name))


def select_targets(
    manifest: Manifest,
    name: str | None,
    *,
    auto_only: bool = False,
) -> list[tuple[Project, RemoteResource]]:
    if name is not None:
        # 名指しは明示された意図なのでmountフラグを無視する
        project = manifest.resolve_project(name)
        if project is None:
            raise ServiceError(f"unknown project: {name}")
        if not isinstance(project.resource, RemoteResource):
            raise ServiceError(f"not a remote resource: {name}")
        return [(project, project.resource)]
    return [
        (project, project.resource)
        for project in manifest.projects
        if isinstance(project.resource, RemoteResource)
        and (not auto_only or project.resource.mount)
    ]


def _group_by_host(
    targets: list[tuple[Project, RemoteResource]],
) -> dict[str, list[tuple[Project, RemoteResource]]]:
    by_host: dict[str, list[tuple[Project, RemoteResource]]] = defaultdict(list)
    for project, resource in targets:
        by_host[resource.host].append((project, resource))
    return by_host


def _remove_if_empty(directory: Path) -> bool:
    """Remove one directory only after confirming it holds no entries."""
    try:
        if any(directory.iterdir()):
            return False
        directory.rmdir()
    except OSError:
        return False
    return True


def _links_to(target: Path, source: Path) -> bool:
    if not target.is_symlink():
        return False
    linked = target.readlink()
    actual = linked if linked.is_absolute() else target.parent / linked
    return Path(normpath(str(actual))) == source


def _ensure_shared_links(
    targets: list[tuple[Project, RemoteResource]],
    mountpoint: Path,
) -> str | None:
    for _, resource in targets:
        target = resource._resolved_workspace_path
        source = aggregated_link_source(resource, mountpoint)
        if target.is_symlink():
            if _links_to(target, source):
                continue
            target.unlink()
        elif target.exists():
            return f"FAIL: workspace path is not a symlink: {target}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
    return None


def _remove_shared_links(
    targets: list[tuple[Project, RemoteResource]],
    mountpoint: Path,
) -> None:
    """Drop the workspace symlinks this mount owns, leaving no dangling links."""
    for _, resource in targets:
        target = resource._resolved_workspace_path
        # mountが作ったlinkだけを消す。実体や無関係なsymlinkには触れない
        if not _links_to(target, aggregated_link_source(resource, mountpoint)):
            continue
        with contextlib.suppress(OSError):
            target.unlink()
        # mountのmkdir(parents=True)と対称に、空になった親だけを畳む
        for parent in list(target.parents)[
            : len(Path(resource.workspace_path).parts) - 1
        ]:
            if not _remove_if_empty(parent):
                break


def _mount_host(
    host_name: str,
    targets: list[tuple[Project, RemoteResource]],
) -> str:
    host = targets[0][1]._resolved_host
    mountpoint = host_mountpoint(host_name)
    health = inspect_host_mount(host_name)
    write_mount_log(
        project=host_name,
        mountpoint=mountpoint,
        stage="precheck",
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
        host.mount_root,
        mountpoint,
        volname=host_volume_name(host_name),
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    options = safe_option_names(cmd)
    write_mount_log(
        project=host_name,
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
            _remove_if_empty(mountpoint)
        return f"FAIL: {result.stderr.strip()}"
    # fuse-t on macOS: mount table lags ~0.2-0.4s behind sshfs exit.
    for _ in range(10):
        health = inspect_host_mount(host_name)
        # slow=健全だが高遅延。unmountすると再mountフラッピングになるため成功扱い
        if health.state in ("ok", "slow"):
            link_error = _ensure_shared_links(targets, mountpoint)
            if link_error:
                return link_error
            write_mount_log(
                project=host_name,
                mountpoint=mountpoint,
                stage="post_mount_probe",
                result=health.state,
                detail=health.detail,
                options=options,
            )
            return "mount"
        if health.state == "unreadable":
            cleanup = _unmount_host(host_name, targets, force=True)
            write_mount_log(
                project=host_name,
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
        _remove_if_empty(mountpoint)
    write_mount_log(
        project=host_name,
        mountpoint=mountpoint,
        stage="post_mount_probe",
        result=health.state,
        detail=health.detail,
        recovery=health.recovery,
        options=options,
    )
    return f"FAIL: {health.state}: {health.detail}; recovery: {health.recovery}"


def _unmount_host(
    host_name: str,
    targets: list[tuple[Project, RemoteResource]],
    force: bool,
) -> str:
    mountpoint = host_mountpoint(host_name)
    health = inspect_host_mount(host_name)
    if health.state == "unmounted":
        _remove_shared_links(targets, mountpoint)
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
    _remove_shared_links(targets, mountpoint)
    _remove_if_empty(mountpoint)
    return "unmount"


def mount_targets(
    manifest: Manifest,
    name: str | None,
    *,
    include_all: bool = False,
) -> list[MountResult]:
    """Mount the selected remote resources, one sshfs per host."""
    if shutil.which("sshfs") is None:
        raise ServiceError("sshfs not found (brew install fuse-t sshfs-fuse-t)")
    targets = select_targets(manifest, name, auto_only=not include_all)
    return [
        MountResult(host_name, _mount_host(host_name, host_targets))
        for host_name, host_targets in _group_by_host(targets).items()
    ]


def unmount_targets(manifest: Manifest, *, force: bool = False) -> list[MountResult]:
    """Unmount every host serving a remote resource."""
    by_host = _group_by_host(select_targets(manifest, None))
    return [
        MountResult(host_name, _unmount_host(host_name, by_host[host_name], force))
        for host_name in sorted(by_host)
    ]
