"""SSH-backed lifecycle for Agent files owned by the Hub."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex

from whub.core.remote import remote_write_file, run_ssh_command
from whub.models import Host
from whub.services.agent.context import AgentContext, CONTEXT_MARKERS
from whub.services.errors import ServiceError
from whub.utils.managed_block import managed_range


def prepare(
    workspace_root: Path,
    project: str,
    task_id: str,
    host: Host,
    worktree: str,
    auth_files: Mapping[PurePosixPath, str],
    agent_context: AgentContext,
) -> None:
    """Materialize Hub-owned files in a remote worktree over SSH.

    The ownership record remains on the Hub so the remote Agent never owns Task
    control-plane state.
    """
    state_path = _state_path(workspace_root, project, task_id)
    previous = _load(state_path)
    if previous is not None and previous["worktree"] != worktree:
        raise ServiceError("remote Agent state does not match the registered worktree")
    files = dict(auth_files) | dict(agent_context.files)
    created_files = _materialize_files(host, worktree, files)
    created_blocks = _materialize_blocks(
        host,
        worktree,
        agent_context.blocks,
        {} if previous is None else previous["blocks"],
    )
    state = {
        "worktree": worktree,
        "files": ({} if previous is None else previous["files"]) | created_files,
        "blocks": ({} if previous is None else previous["blocks"]) | created_blocks,
    }
    if state["files"] or state["blocks"]:
        _save(state_path, state)


def cleanup(
    workspace_root: Path, project: str, task_id: str, host: Host, worktree: str
) -> None:
    """Remove only unchanged Hub-owned remote Agent files."""
    state_path = _state_path(workspace_root, project, task_id)
    state = _load(state_path)
    if state is None:
        return
    if state["worktree"] != worktree:
        raise ServiceError("remote Agent state does not match the registered worktree")
    _cleanup_files(host, worktree, state["files"])
    _cleanup_blocks(host, worktree, state["blocks"])
    state_path.unlink()


def _remote_path(worktree: str, relative: PurePosixPath) -> str:
    if relative.is_absolute() or ".." in relative.parts:
        raise ServiceError(f"invalid generated config path: {relative}")
    return str(PurePosixPath(worktree) / relative)


def _run(host: Host, command: str) -> str:
    result = run_ssh_command(host, command)
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise ServiceError(f"remote Agent state operation failed: {detail}")
    return result.stdout


def _validate_path(host: Host, worktree: str, relative: PurePosixPath) -> str:
    path = _remote_path(worktree, relative)
    current = PurePosixPath(worktree)
    for part in relative.parts:
        current /= part
        if _run(host, f"test ! -L {shlex.quote(str(current))}") is None:
            raise AssertionError("unreachable")
    return path


def _read(host: Host, path: str) -> str | None:
    exists = run_ssh_command(host, f"test -e {shlex.quote(path)}")
    if exists.returncode != 0:
        return None
    result = run_ssh_command(host, f"cat -- {shlex.quote(path)}")
    if result.returncode == 0:
        return result.stdout
    detail = result.stderr.strip() or f"exit status {result.returncode}"
    raise ServiceError(f"remote Agent state operation failed: {detail}")


def _write(host: Host, path: str, content: str) -> None:
    _run(host, f"mkdir -p -- {shlex.quote(str(PurePosixPath(path).parent))}")
    result = remote_write_file(host, path, content)
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise ServiceError(f"remote Agent state operation failed: {detail}")


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _materialize_files(
    host: Host, worktree: str, files: Mapping[PurePosixPath, str]
) -> dict[str, str]:
    created: dict[str, str] = {}
    for relative, content in files.items():
        path = _validate_path(host, worktree, relative)
        existing = _read(host, path)
        if existing is None:
            _write(host, path, content)
            created[str(relative)] = _digest(content)
        elif existing != content:
            raise ServiceError(f"generated config already exists: {relative}")
    return created


def _materialize_blocks(
    host: Host,
    worktree: str,
    blocks: Mapping[PurePosixPath, str],
    owned: object,
) -> dict[str, str]:
    if not isinstance(owned, dict):
        raise ServiceError("invalid remote Agent state")
    created: dict[str, str] = {}
    for relative, block in blocks.items():
        path = _validate_path(host, worktree, relative)
        content = _read(host, path)
        if content is None:
            _write(host, path, block)
            created[str(relative)] = _digest(block)
            continue
        try:
            start, end = _block_range(content, relative)
        except ServiceError:
            if str(relative) in owned:
                raise
            separator = "" if not content or content.endswith("\n\n") else "\n"
            _write(host, path, content + separator + block)
            created[str(relative)] = _digest(block)
            continue
        if str(relative) not in owned:
            raise ServiceError(f"managed context already exists: {relative}")
        if _digest(content[start:end]) != owned[str(relative)]:
            raise ServiceError(f"managed context was modified: {relative}")
    return created


def _cleanup_files(host: Host, worktree: str, files: object) -> None:
    if not isinstance(files, dict):
        raise ServiceError("invalid remote Agent state")
    for name, expected in files.items():
        relative = PurePosixPath(name)
        path = _validate_path(host, worktree, relative)
        content = _read(host, path)
        if content is None:
            continue
        if not isinstance(expected, str) or _digest(content) != expected:
            raise ServiceError(f"generated config was modified and was not removed: {relative}")
        _run(host, f"rm -- {shlex.quote(path)}")


def _cleanup_blocks(host: Host, worktree: str, blocks: object) -> None:
    if not isinstance(blocks, dict):
        raise ServiceError("invalid remote Agent state")
    for name, expected in blocks.items():
        relative = PurePosixPath(name)
        path = _validate_path(host, worktree, relative)
        content = _read(host, path)
        if content is None:
            raise ServiceError(f"managed context is missing: {relative}")
        start, end = _block_range(content, relative)
        if not isinstance(expected, str) or _digest(content[start:end]) != expected:
            raise ServiceError(f"managed context was modified and was not removed: {relative}")
        remaining = content[:start].rstrip("\n") + content[end:]
        if remaining.strip():
            _write(host, path, remaining)
        else:
            _run(host, f"rm -- {shlex.quote(path)}")


def _block_range(content: str, relative: PurePosixPath) -> tuple[int, int]:
    try:
        bounds = managed_range(content, CONTEXT_MARKERS)
    except ValueError as error:
        raise ServiceError(f"invalid managed context: {relative}") from error
    if bounds is None:
        raise ServiceError(f"managed context is missing: {relative}")
    return bounds


def _state_path(workspace_root: Path, project: str, task_id: str) -> Path:
    return workspace_root / "projects/worktrees/agents" / f"{project}-{task_id.removeprefix('TASK-')}.remote.json"


def _load(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or not isinstance(data.get("worktree"), str):
            raise ValueError("invalid fields")
        for key in ("files", "blocks"):
            if not isinstance(data.get(key), dict) or not all(
                isinstance(name, str) and isinstance(value, str)
                for name, value in data[key].items()
            ):
                raise ValueError("invalid fields")
        return data
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ServiceError(f"invalid remote Agent state: {path}: {error}") from error


def _save(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, sort_keys=True) + "\n")
