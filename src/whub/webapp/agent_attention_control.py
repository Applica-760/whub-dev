"""Forward Codex Hook events to the local web backend."""

from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from whub.core.context import WhubContext
from whub.services.errors import ServiceError
from whub.webapp.runner import read_pid_record


_COMMON_FIELDS = ("hook_event_name", "session_id", "cwd", "turn_id")
_TOOL_EVENTS = ("PermissionRequest", "PostToolUse")


def submit(context: WhubContext, event: Mapping[str, object]) -> None:
    """Submit one supported Hook event or raise a local control-plane error."""
    payload = _payload(event)
    process = read_pid_record(context.app_dev_pid_path) or read_pid_record(
        context.app_pid_path
    )
    if process is None:
        raise ServiceError("whub web app is not running")
    request = Request(
        f"http://127.0.0.1:{process.port}/api/agent-attention/events",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=3):
            pass
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise ServiceError(f"attention hook request failed: {detail}") from error
    except URLError as error:
        raise ServiceError(f"attention hook request failed: {error.reason}") from error


def _payload(event: Mapping[str, object]) -> dict[str, str]:
    payload = {field: event.get(field) for field in _COMMON_FIELDS}
    event_name = payload["hook_event_name"]
    if event_name not in (*_TOOL_EVENTS, "Stop") or any(
        not isinstance(value, str) or not value for value in payload.values()
    ):
        raise ServiceError("invalid Codex Hook event")
    tool_name = event.get("tool_name")
    if event_name in _TOOL_EVENTS:
        if not isinstance(tool_name, str) or not tool_name:
            raise ServiceError("invalid Codex Hook event")
        payload["tool_name"] = tool_name
    operator_id = event.get("operator_id")
    if operator_id is not None:
        if not isinstance(operator_id, str) or not operator_id:
            raise ServiceError("invalid Codex Hook event")
        payload["operator_id"] = operator_id
    return {field: value for field, value in payload.items() if isinstance(value, str)}
