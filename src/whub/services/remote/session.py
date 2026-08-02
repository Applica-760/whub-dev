"""Remote GUI session reservation, inspection, and cleanup."""

from __future__ import annotations

from datetime import datetime
from importlib.resources import files
import json
import re
import shlex
import subprocess
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from whub.core.remote import build_ssh_command, run_ssh_command
from whub.core.target import (
    TargetError,
    require_resource_type,
    resolve_project_resource,
)
from whub.models import Manifest, RemoteResource, SessionDescriptor
from whub.services.errors import ServiceError
from whub.utils.process import format_process_error


_JST = ZoneInfo("Asia/Tokyo")


def _resource(manifest: Manifest, project: str) -> RemoteResource:
    try:
        return require_resource_type(
            resolve_project_resource(manifest, project), RemoteResource, project
        )
    except TargetError as error:
        raise ServiceError(str(error)) from error


def _validate_run_id(run_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id) is None:
        raise ServiceError(f"invalid run ID: {run_id}")
    return run_id


def _operation_script(name: str) -> str:
    return files("whub").joinpath("assets", "session", "operations", name).read_text()


def _python(
    resource: RemoteResource, script: str, *args: str, input: str | None = None
) -> str:
    command = shlex.join(("python3", "-c", script, resource.remote_path, *args))
    try:
        result = run_ssh_command(
            resource._resolved_host, command, input=input, check=True
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ServiceError(
            f"remote session operation failed: {format_process_error(error)}"
        ) from error
    return result.stdout


def reserve_session(manifest: Manifest, project: str, task: str | None = None) -> str:
    resource = _resource(manifest, project)
    if task and task.isdigit():
        task = f"TASK-{int(task):03}"
    if task and re.fullmatch(r"TASK-[0-9]+", task) is None:
        raise ServiceError(f"invalid task ID: {task}")
    assets = {
        "session-launcher.py": files("whub")
        .joinpath("assets", "session", "launcher.py")
        .read_text(),
        "session-launcher.sh": files("whub")
        .joinpath("assets", "session", "launcher.sh")
        .read_text(),
    }
    payload = json.dumps({"project": project, "task": task, "assets": assets})
    return _python(resource, _operation_script("reserve.py"), input=payload).strip()


def list_sessions(manifest: Manifest, project: str) -> list[SessionDescriptor]:
    resource = _resource(manifest, project)
    try:
        return [
            SessionDescriptor.model_validate(item)
            for item in json.loads(_python(resource, _operation_script("list.py")))
        ]
    except (json.JSONDecodeError, ValidationError) as error:
        raise ServiceError(f"invalid remote session descriptor: {error}") from error


def get_session(manifest: Manifest, project: str, run_id: str) -> SessionDescriptor:
    resource = _resource(manifest, project)
    run_id = _validate_run_id(run_id)
    try:
        items = json.loads(_python(resource, _operation_script("list.py"), run_id))
        if not items:
            raise ServiceError(f"unknown run: {run_id}")
        return SessionDescriptor.model_validate(items[0])
    except (json.JSONDecodeError, ValidationError) as error:
        raise ServiceError(f"invalid remote session descriptor: {error}") from error


def clean_session(manifest: Manifest, project: str, run_id: str) -> None:
    _python(
        _resource(manifest, project),
        _operation_script("clean.py"),
        _validate_run_id(run_id),
    )


def write_session_handoff(
    manifest: Manifest,
    project: str,
    run_id: str,
    purpose: str,
    command: str,
) -> None:
    """Prepend one copy-only command entry to a remote session handoff file."""
    resource = _resource(manifest, project)
    run_id = _validate_run_id(run_id)
    purpose = purpose.strip()
    if not purpose or "\n" in purpose or "\r" in purpose:
        raise ServiceError("handoff purpose must be one non-empty line")
    if not command.strip():
        raise ServiceError("handoff command must not be empty")
    payload = json.dumps(
        {
            "run_id": run_id,
            "purpose": purpose,
            "command": command,
            "timestamp": datetime.now(_JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        }
    )
    _python(resource, _operation_script("handoff.py"), run_id, input=payload)


def read_session_logs(
    manifest: Manifest, project: str, run_id: str, pane: str | None = None
) -> str:
    resource = _resource(manifest, project)
    descriptor = get_session(manifest, project, run_id)
    selected = [
        item
        for item in descriptor.panes
        if pane is None or pane in {item.pane_id, item.window_name}
    ]
    if pane is not None and not selected:
        raise ServiceError(f"unknown pane: {pane}")
    if pane is not None and len(selected) > 1:
        raise ServiceError(f"ambiguous pane name: {pane}")
    output = []
    for item in selected:
        remote = (
            f"cd {shlex.quote(resource.remote_path)} && "
            f"cat {shlex.quote(item.transcript)}"
        )
        result = run_ssh_command(resource._resolved_host, remote)
        output.append(f"== {item.window_name} {item.pane_id} ==\n{result.stdout}")
    return "".join(output)


def build_follow_logs_command(
    manifest: Manifest, project: str, run_id: str, pane: str | None = None
) -> list[str]:
    resource = _resource(manifest, project)
    descriptor = get_session(manifest, project, run_id)
    candidates = [
        item
        for item in descriptor.panes
        if pane is None or pane in {item.pane_id, item.window_name}
    ]
    if len(candidates) != 1:
        raise ServiceError("logs --follow requires one unambiguous pane")
    remote = (
        f"cd {shlex.quote(resource.remote_path)} && exec tail -n 20 -F "
        f"{shlex.quote(candidates[0].transcript)}"
    )
    return build_ssh_command(resource._resolved_host, remote)
