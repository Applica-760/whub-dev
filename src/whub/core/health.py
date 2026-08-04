"""Resource health inspection shared by commands."""

from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path
from posixpath import normpath
from typing import Literal
from whub.models.manifest import RemoteResource, SymlinkResource

HealthState = Literal[
    "ok",
    "missing",
    "source-missing",
    "broken",
    "wrong-target",
    "unexpected",
    "unreachable",
    "unmounted",
    "stale",
    "unreadable",
    "slow",
]

ProbeOutcome = Literal["ok", "denied", "timeout", "error"]


@dataclass(frozen=True)
class ResourceHealth:
    state: HealthState
    detail: str | None = None
    recovery: str | None = None


@dataclass(frozen=True)
class DirectoryProbe:
    outcome: ProbeOutcome
    detail: str | None = None


def probe_directory_readable(path: Path, timeout: int = 3) -> DirectoryProbe:
    """Probe directory enumeration in a timeout-isolated process."""
    try:
        result = subprocess.run(
            ["ls", "-A", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # 遅延は障害ではない: 判定契約 mount_health_latency_independent
        return DirectoryProbe("timeout", f"directory listing exceeded {timeout}s")
    except OSError as error:
        return DirectoryProbe("error", f"directory listing failed: {error}")
    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or f"directory listing failed: exit {result.returncode}"
        )
        if "operation not permitted" in detail.lower():
            return DirectoryProbe("denied", detail)
        return DirectoryProbe("error", detail)
    return DirectoryProbe("ok")


def inspect_symlink(
    resource: SymlinkResource, target: Path | None = None
) -> ResourceHealth:
    if target is None:
        target = getattr(resource, "_resolved_workspace_path", None)
        target = Path(resource.workspace_path) if target is None else target
    source = Path(resource.source).expanduser()

    if not source.exists():
        return ResourceHealth("source-missing", str(source))
    if target.is_symlink():
        try:
            resolved_target = target.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            return ResourceHealth("broken", str(error))
        if resolved_target == source.resolve():
            return ResourceHealth("ok")
        return ResourceHealth("wrong-target", str(resolved_target))
    if target.exists():
        return ResourceHealth("unexpected", str(target))
    return ResourceHealth("missing", str(target))


def _read_mount_table() -> str | None:
    """`mount(1)`の出力。ハングや失敗で読めないときはNone。"""
    try:
        result = subprocess.run(["mount"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def inspect_mountpoint(mountpoint: Path, volname: str) -> ResourceHealth:
    """Inspect one sshfs mountpoint using its expected volume name."""
    table = _read_mount_table()
    # テーブルを読めない＝状態不明。unmountがskipしないようstale扱い（fail-safe）
    if table is None:
        return ResourceHealth(
            "stale",
            "mount table unreadable",
            "retry; if persistent, run `whub unmount --force`",
        )
    in_mount_table = any(f" on {mountpoint} (" in line for line in table.splitlines())
    if not in_mount_table:
        return ResourceHealth("unmounted", str(mountpoint), "run `whub mount`")
    try:
        process = subprocess.run(
            ["pgrep", "-f", f"volname={volname}"],
            capture_output=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return ResourceHealth(
            "stale", str(error), "run `whub unmount --force`, then `whub mount`"
        )
    if process.returncode != 0:
        return ResourceHealth(
            "stale",
            f"sshfs process missing: {volname}",
            "run `whub unmount --force`, then `whub mount`",
        )
    try:
        # stale mountはstatがブロックするため、子プロセス＋timeoutで隔離する
        subprocess.run(
            ["stat", str(mountpoint)],
            capture_output=True,
            timeout=3,
            check=True,
        )
    except subprocess.TimeoutExpired:
        # sshfsプロセス生存確認済みのため遅延とみなす（stale=プロセス消失・table不明に限定）
        return ResourceHealth("slow", f"stat exceeded 3s: {mountpoint}")
    except (OSError, subprocess.CalledProcessError) as error:
        return ResourceHealth(
            "stale",
            str(error),
            "run `whub unmount --force`, then `whub mount`",
        )
    probe = probe_directory_readable(mountpoint)
    if probe.outcome == "denied":
        return ResourceHealth(
            "unreadable",
            probe.detail,
            "allow Network Volumes access for this app, then remount",
        )
    if probe.outcome == "timeout":
        return ResourceHealth("slow", probe.detail)
    if probe.outcome == "error":
        return ResourceHealth(
            "stale",
            probe.detail,
            "run `whub unmount --force`, then `whub mount`",
        )
    return ResourceHealth("ok")


def inspect_aggregated_mount(
    resource: RemoteResource,
    host_mountpoint: Path,
    host_volname: str,
    target: Path | None = None,
) -> ResourceHealth:
    """Combine a workspace symlink check with its shared host mount health."""
    source = host_mountpoint / resource.path
    if target is None:
        target = getattr(resource, "_resolved_workspace_path", None)
        target = Path(resource.workspace_path) if target is None else target

    if not target.is_symlink():
        if target.exists():
            return ResourceHealth("unexpected", str(target))
        return ResourceHealth("missing", str(target), "run `whub mount`")
    try:
        linked = target.readlink()
    except OSError as error:
        return ResourceHealth("broken", str(error), "run `whub mount`")
    actual = linked if linked.is_absolute() else target.parent / linked
    if Path(normpath(str(actual))) != source:
        return ResourceHealth("wrong-target", str(actual), "run `whub mount`")

    host_health = inspect_mountpoint(host_mountpoint, host_volname)
    if host_health.state != "ok":
        return host_health
    try:
        result = subprocess.run(
            ["stat", str(target)],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except subprocess.TimeoutExpired:
        return ResourceHealth("slow", f"stat exceeded 3s: {target}")
    except OSError as error:
        return ResourceHealth("broken", str(error), "run `whub mount`")
    if result.returncode != 0:
        detail = result.stderr.strip() or f"stat failed: exit {result.returncode}"
        if "operation not permitted" in detail.lower():
            return ResourceHealth(
                "unreadable",
                detail,
                "allow Network Volumes access for this app, then remount",
            )
        return ResourceHealth("broken", detail, "run `whub mount`")
    return ResourceHealth("ok")
