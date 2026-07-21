"""Remote GUI session reservation, inspection, and cleanup."""
from __future__ import annotations

from importlib.resources import files
import json
import re
import shlex
import subprocess

import yaml
from pydantic import ValidationError

from whub.core.remote import build_ssh_command, run_ssh_command
from whub.core.target import TargetError, require_resource_type, resolve_project_resource
from whub.models import Manifest, RemoteResource, SessionDescriptor
from whub.services.errors import ServiceError
from whub.utils.process import format_process_error


_RESERVE = r"""
import json, os, re, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required")
root = Path(sys.argv[1])
payload = json.load(sys.stdin)
runtime = root / ".whub"
sessions = runtime / "sessions"
runs = runtime / "runs"
for path in (runtime, sessions, runs):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
gitignore = root / ".gitignore"
start, end = "# whub session:start", "# whub session:end"
existing = gitignore.read_text() if gitignore.exists() else ""
block = f"{start}\n.whub/\n{end}\n"
if start not in existing and end not in existing:
    content = block + ("\n" + existing if existing else "")
elif existing.count(start) == existing.count(end) == 1 and existing.index(start) < existing.index(end):
    content = existing[:existing.index(start)] + block + existing[existing.index(end) + len(end):].lstrip("\n")
else:
    raise SystemExit("invalid whub session markers in .gitignore")
def replace(path, text, mode):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text); stream.flush(); os.fsync(stream.fileno())
        tmp.chmod(mode); os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
if content != existing:
    replace(gitignore, content, 0o644)
for name in ("session-launcher.py", "session-launcher.sh"):
    asset = runtime / name
    content = payload["assets"][name]
    if not asset.exists() or asset.read_text() != content:
        replace(asset, content, 0o600)
prefix = payload["task"] or "adhoc"
pattern = re.compile(re.escape(prefix) + r"-r([0-9]+)\.yaml$")
number = max((int(m.group(1)) for p in sessions.glob(f"{prefix}-r*.yaml") if (m := pattern.match(p.name))), default=0)
while True:
    number += 1
    run_id = f"{prefix}-r{number:03}"
    path = sessions / f"{run_id}.yaml"
    now = datetime.now(timezone.utc).isoformat()
    data = {"schema_version": 1, "protocol_version": 1, "project": payload["project"],
            "task": payload["task"], "run_id": run_id, "state": "pending",
            "created_at": now, "updated_at": now, "tmux": None, "panes": []}
    fd, name = tempfile.mkstemp(dir=sessions, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
            stream.flush(); os.fsync(stream.fileno())
        tmp.chmod(0o600)
        try:
            os.link(tmp, path)
            print(run_id)
            break
        except FileExistsError:
            continue
    finally:
        tmp.unlink(missing_ok=True)
"""

_LIST = r"""
import json, sys
from pathlib import Path
import yaml
root = Path(sys.argv[1])
requested = sys.argv[2] if len(sys.argv) > 2 else None
paths = [root / ".whub" / "sessions" / f"{requested}.yaml"] if requested else sorted((root / ".whub" / "sessions").glob("*.yaml"))
items = []
for path in paths:
    if not path.is_file():
        continue
    items.append(yaml.safe_load(path.read_text()))
print(json.dumps(items, default=str))
"""

_CLEAN = r"""
import shutil, subprocess, sys
from pathlib import Path
import yaml
root, run_id = Path(sys.argv[1]), sys.argv[2]
path = root / ".whub" / "sessions" / f"{run_id}.yaml"
if not path.is_file():
    raise SystemExit(f"unknown run: {run_id}")
data = yaml.safe_load(path.read_text())
if data["state"] == "running":
    raise SystemExit(f"run is still running: {run_id}")
if data.get("tmux"):
    subprocess.run(["tmux", "-S", data["tmux"]["socket"], "kill-session", "-t", f"={data['tmux']['session']}"], capture_output=True)
shutil.rmtree(root / ".whub" / "runs" / run_id, ignore_errors=True)
path.unlink()
"""


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


def _python(resource: RemoteResource, script: str, *args: str, input: str | None = None) -> str:
    command = shlex.join(("python3", "-c", script, resource.path, *args))
    try:
        result = run_ssh_command(resource._resolved_host, command, input=input, check=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise ServiceError(f"remote session operation failed: {format_process_error(error)}") from error
    return result.stdout


def reserve_session(manifest: Manifest, project: str, task: str | None = None) -> str:
    resource = _resource(manifest, project)
    if task and task.isdigit():
        task = f"TASK-{int(task):03}"
    if task and re.fullmatch(r"TASK-[0-9]+", task) is None:
        raise ServiceError(f"invalid task ID: {task}")
    assets = {
        "session-launcher.py": files("whub").joinpath("session/launcher.py").read_text(),
        "session-launcher.sh": files("whub").joinpath("session/launcher.sh").read_text(),
    }
    payload = json.dumps({"project": project, "task": task, "assets": assets})
    return _python(resource, _RESERVE, input=payload).strip()


def list_sessions(manifest: Manifest, project: str) -> list[SessionDescriptor]:
    resource = _resource(manifest, project)
    try:
        return [SessionDescriptor.model_validate(item) for item in json.loads(_python(resource, _LIST))]
    except (json.JSONDecodeError, ValidationError) as error:
        raise ServiceError(f"invalid remote session descriptor: {error}") from error


def get_session(manifest: Manifest, project: str, run_id: str) -> SessionDescriptor:
    resource = _resource(manifest, project)
    run_id = _validate_run_id(run_id)
    try:
        items = json.loads(_python(resource, _LIST, run_id))
        if not items:
            raise ServiceError(f"unknown run: {run_id}")
        return SessionDescriptor.model_validate(items[0])
    except (json.JSONDecodeError, ValidationError) as error:
        raise ServiceError(f"invalid remote session descriptor: {error}") from error


def clean_session(manifest: Manifest, project: str, run_id: str) -> None:
    _python(_resource(manifest, project), _CLEAN, _validate_run_id(run_id))


def read_session_logs(
    manifest: Manifest, project: str, run_id: str, pane: str | None = None
) -> str:
    resource = _resource(manifest, project)
    descriptor = get_session(manifest, project, run_id)
    selected = [
        item for item in descriptor.panes
        if pane is None or pane in {item.pane_id, item.window_name}
    ]
    if pane is not None and not selected:
        raise ServiceError(f"unknown pane: {pane}")
    if pane is not None and len(selected) > 1:
        raise ServiceError(f"ambiguous pane name: {pane}")
    output = []
    for item in selected:
        command = f"cd {shlex.quote(resource.path)} && cat {shlex.quote(item.transcript)}"
        result = run_ssh_command(resource._resolved_host, command)
        output.append(f"== {item.window_name} {item.pane_id} ==\n{result.stdout}")
    return "".join(output)


def build_follow_logs_command(
    manifest: Manifest, project: str, run_id: str, pane: str | None = None
) -> list[str]:
    resource = _resource(manifest, project)
    descriptor = get_session(manifest, project, run_id)
    candidates = [
        item for item in descriptor.panes
        if pane is None or pane in {item.pane_id, item.window_name}
    ]
    if len(candidates) != 1:
        raise ServiceError("logs --follow requires one unambiguous pane")
    remote = f"cd {shlex.quote(resource.path)} && exec tail -n 20 -F {shlex.quote(candidates[0].transcript)}"
    return build_ssh_command(resource._resolved_host, remote)
