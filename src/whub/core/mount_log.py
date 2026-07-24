"""Bounded, best-effort diagnostics for mount operations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from whub.core.context import current_context
from whub.core.release import current_release

_MAX_RECORDS = 100
_SAFE_OPTIONS = {
    "-s",
    "ServerAliveCountMax",
    "ServerAliveInterval",
    "defer_permissions",
    "noappledouble",
    "noapplexattr",
    "port",
    "reconnect",
    "volname",
}


def safe_option_names(command: list[str]) -> list[str]:
    names: list[str] = []
    for index, value in enumerate(command):
        candidate = value
        if index and command[index - 1] == "-o":
            candidate = value.split("=", 1)[0]
        if candidate in _SAFE_OPTIONS and candidate not in names:
            names.append(candidate)
    return names


def write_mount_log(
    *,
    project: str,
    mountpoint: Path,
    stage: str,
    result: str,
    detail: str | None = None,
    recovery: str | None = None,
    options: list[str] | None = None,
) -> None:
    """Append one redacted record without affecting the mount operation."""
    try:
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": current_release().release_id,
            "project": project,
            "mountpoint": str(mountpoint),
            "stage": stage,
            "options": options or [],
            "result": result,
            "detail": detail,
            "recovery": recovery,
        }
        path = current_context().directory / "runtime" / "logs" / "mount.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = path.read_text().splitlines() if path.exists() else []
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
        path.write_text("\n".join(lines[-_MAX_RECORDS:]) + "\n")
    except Exception:
        return
