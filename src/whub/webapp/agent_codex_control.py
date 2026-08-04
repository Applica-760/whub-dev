"""Request App Server lifecycle changes from the local web backend."""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from whub.core.context import WhubContext
from whub.services.errors import ServiceError
from whub.webapp.runner import HOST, read_pid_record


def start(context: WhubContext, project: str, task_id: str) -> None:
    _request(context, "POST", project, task_id)


def stop(context: WhubContext, project: str, task_id: str) -> None:
    _request(context, "DELETE", project, task_id)


def _request(context: WhubContext, method: str, project: str, task_id: str) -> None:
    process = read_pid_record(context.app_dev_pid_path) or read_pid_record(
        context.app_pid_path
    )
    if process is None:
        raise ServiceError("whub web app is not running")
    request = Request(
        f"http://{HOST}:{process.port}/api/agent-codex/{project}/{task_id}/session",
        method=method,
    )
    try:
        with urlopen(request, timeout=3):
            pass
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise ServiceError(f"App Server control request failed: {detail}") from error
    except URLError as error:
        raise ServiceError(
            f"App Server control request failed: {error.reason}"
        ) from error
