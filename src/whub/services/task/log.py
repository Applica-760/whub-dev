"""Structured Task activity log entries stored in Markdown."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Literal, cast, get_args

from whub.services.flow.errors import FlowError
from whub.services.task.common import load_task_markdown, write_task_markdown

LogKind = Literal["fact", "analysis", "proposal"]


def append_task_log(task_path: Path, payload: str, now: datetime | None = None) -> None:
    """Validate one JSON log entry and append it to TASK_PATH's Markdown."""
    kind, message = _parse_log(payload)
    timestamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
    content = load_task_markdown(task_path).rstrip()
    write_task_markdown(task_path, f"{content}\n\n- {timestamp} | {kind} | {message}\n")


def _parse_log(payload: str) -> tuple[LogKind, str]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise FlowError(f"task log must be JSON: {error.msg}") from error
    if not isinstance(value, dict) or len(value) != 1:
        raise FlowError("task log must be one key-value pair")
    kind, message = next(iter(value.items()))
    if (
        kind not in get_args(LogKind)
        or not isinstance(message, str)
        or not message.strip()
    ):
        raise FlowError("task log requires one LogKind key and a non-empty string")
    return cast(LogKind, kind), message.strip()
