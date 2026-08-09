"""Structured Task activity log entries stored in Markdown."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Literal, cast, get_args

from whub.services.flow.errors import FlowError
from whub.services.task.common import load_task_markdown, write_task_markdown
from whub.utils.managed_block import (
    format_block,
    insert_before_end_marker,
    managed_range,
)


LogKind = Literal["fact", "analysis", "proposal"]
_MARKERS = ("<!-- whub:task-log:start -->", "<!-- whub:task-log:end -->")


def append_task_log(
    task_path: Path, payload: str, actor: str, now: datetime | None = None
) -> None:
    """Validate one JSON log entry and append it to TASK_PATH's Markdown."""
    kind, message = _parse_log(payload)
    if not actor.strip():
        raise FlowError("task log actor must be non-empty")
    content = load_task_markdown(task_path)
    try:
        if managed_range(content, _MARKERS) is None:
            content = content.rstrip() + "\n\n" + format_block(_MARKERS, "")
        timestamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
        content = insert_before_end_marker(
            content, f"- {timestamp} | {actor.strip()} | {kind} | {message}\n", _MARKERS
        )
    except ValueError as error:
        raise FlowError(f"invalid task log block: {error}") from error
    write_task_markdown(task_path, content)


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
