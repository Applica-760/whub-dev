"""Resource health inspection shared by commands."""

from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from whub.models import RemoteResource, SymlinkResource

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
]


@dataclass(frozen=True)
class ResourceHealth:
    state: HealthState
    detail: str | None = None
    recovery: str | None = None


def probe_directory_readable(path: Path, timeout: int = 3) -> str | None:
    """Probe directory enumeration in a timeout-isolated process."""
    try:
        result = subprocess.run(
            ["ls", "-A", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"directory listing timed out after {timeout}s"
    except OSError as error:
        return f"directory listing failed: {error}"
    if result.returncode != 0:
        return (
            result.stderr.strip()
            or f"directory listing failed: exit {result.returncode}"
        )
    return None


def inspect_symlink(resource: SymlinkResource) -> ResourceHealth:
    target = resource._resolved_workspace_path
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


def inspect_mount(resource: RemoteResource, project_name: str) -> ResourceHealth:
    mountpoint = resource._resolved_workspace_path
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
            ["pgrep", "-f", f"volname=whub-{project_name}"],
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
            f"sshfs process missing: whub-{project_name}",
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
        return ResourceHealth(
            "stale",
            str(mountpoint),
            "run `whub unmount --force`, then `whub mount`",
        )
    except (OSError, subprocess.CalledProcessError) as error:
        return ResourceHealth(
            "stale",
            str(error),
            "run `whub unmount --force`, then `whub mount`",
        )
    if error := probe_directory_readable(mountpoint):
        return ResourceHealth(
            "unreadable",
            error,
            "allow Network Volumes access for this app, then remount",
        )
    return ResourceHealth("ok")
