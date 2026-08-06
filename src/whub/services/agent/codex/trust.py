"""Manage a worktree-scoped Codex trust entry owned by whub."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import tempfile
import tomllib
from contextlib import contextmanager

from whub.core.remote import remote_write_file, run_ssh_command
from whub.models import Host
from whub.services.errors import ServiceError


def prepare(
    workspace_root: Path,
    project: str,
    task_id: str,
    worktree: Path,
    *,
    codex_home: Path | None = None,
) -> None:
    """Trust WORKTREE in Codex, recording only a whub-owned config block."""
    state_path = _state_path(workspace_root, project, task_id)
    existing = _load_state(state_path)
    if existing is not None:
        if existing["worktree"] != str(worktree):
            raise ServiceError(
                "Codex trust state does not match the registered worktree"
            )
        _validate_owned_block(Path(existing["config_path"]), existing["block"])
        return

    config_path = (
        Path.home() / ".codex" if codex_home is None else codex_home
    ) / "config.toml"
    content = _read_config(config_path)
    project_config = _project_config(content, worktree)
    if project_config is not None:
        if project_config.get("trust_level") == "trusted":
            return
        raise ServiceError(f"Codex project trust already exists for: {worktree}")

    block = _block(worktree)
    _write_config(config_path, _append_block(content, block))
    _save_state(
        state_path,
        {
            "config_path": str(config_path),
            "worktree": str(worktree),
            "block": block,
        },
    )


def cleanup(workspace_root: Path, project: str, task_id: str, worktree: Path) -> None:
    """Remove only the unchanged Codex trust entry created by whub."""
    state_path = _state_path(workspace_root, project, task_id)
    state = _load_state(state_path)
    if state is None:
        return
    if state["worktree"] != str(worktree):
        raise ServiceError("Codex trust state does not match the registered worktree")
    config_path = Path(state["config_path"])
    content = _read_config(config_path)
    block = state["block"]
    if content.count(block) != 1:
        raise ServiceError(
            "whub-owned Codex trust entry was modified and was not removed"
        )
    _write_config(config_path, _remove_block(content, block))
    state_path.unlink()


def _project_config(content: str, worktree: Path) -> dict[str, object] | None:
    if not content.strip():
        return None
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise ServiceError(f"invalid Codex config: {error}") from error
    projects = data.get("projects")
    if projects is None:
        return None
    if not isinstance(projects, dict):
        raise ServiceError("invalid Codex config: projects must be a table")
    value = projects.get(str(worktree))
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ServiceError("invalid Codex config: project trust must be a table")
    return value


def _block(worktree: Path) -> str:
    identifier = hashlib.sha256(str(worktree).encode()).hexdigest()[:16]
    return (
        f"# whub:codex-trust:{identifier}:start\n"
        f"[projects.{json.dumps(str(worktree))}]\n"
        'trust_level = "trusted"\n'
        f"# whub:codex-trust:{identifier}:end\n"
    )


def _append_block(content: str, block: str) -> str:
    if not content:
        return block
    return content.rstrip("\n") + "\n\n" + block


def _remove_block(content: str, block: str) -> str:
    remaining = content.replace(block, "", 1)
    return remaining.replace("\n\n\n", "\n\n").lstrip("\n")


def _read_config(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_symlink() or not path.is_file():
        raise ServiceError(f"Codex config is not a regular file: {path}")
    return path.read_text(encoding="utf-8")


def _write_config(path: Path, content: str) -> None:
    if not content:
        if path.exists():
            path.unlink()
        return
    if path.parent.exists() and path.parent.is_symlink():
        raise ServiceError(f"Codex config directory is a symlink: {path.parent}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _state_path(workspace_root: Path, project: str, task_id: str) -> Path:
    return (
        workspace_root
        / "projects"
        / "worktrees"
        / "agents"
        / f"{project}-{task_id.removeprefix('TASK-')}.codex-trust.json"
    )


def _load_state(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not all(
            isinstance(data.get(key), str)
            for key in ("config_path", "worktree", "block")
        ):
            raise ValueError("invalid fields")
        return data
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ServiceError(f"invalid Codex trust state: {path}: {error}") from error


def _save_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        json.dump(state, temporary, sort_keys=True)
        temporary.write("\n")
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _validate_owned_block(path: Path, block: str) -> None:
    if _read_config(path).count(block) != 1:
        raise ServiceError("whub-owned Codex trust entry was modified")


def prepare_remote(
    workspace_root: Path, project: str, task_id: str, host: Host, worktree: str
) -> None:
    """Trust a remote worktree, using SSH only as this service's transport."""
    state_path = _remote_state_path(workspace_root, project, task_id)
    existing = _load_remote_state(state_path)
    config_path = (
        existing["config_path"] if existing is not None else _remote_config_path(host)
    )
    with _remote_config_lock(host, config_path):
        if existing is not None:
            if existing["worktree"] != worktree:
                raise ServiceError(
                    "remote Codex trust state does not match the registered worktree"
                )
            if _read_remote_config(host, config_path).count(existing["block"]) != 1:
                raise ServiceError("whub-owned remote Codex trust entry was modified")
            return
        content = _read_remote_config(host, config_path)
        project_config = _project_config(content, Path(worktree))
        if project_config is not None:
            if project_config.get("trust_level") == "trusted":
                return
            raise ServiceError(f"Codex project trust already exists for: {worktree}")
        block = _block(Path(worktree))
        _write_remote_config(host, config_path, _append_block(content, block))
    _save_remote_state(
        state_path,
        {"config_path": config_path, "worktree": worktree, "block": block},
    )


def cleanup_remote(
    workspace_root: Path, project: str, task_id: str, host: Host, worktree: str
) -> None:
    """Remove only this service's unchanged remote Codex trust entry."""
    state_path = _remote_state_path(workspace_root, project, task_id)
    state = _load_remote_state(state_path)
    if state is None:
        return
    if state["worktree"] != worktree:
        raise ServiceError("remote Codex trust state does not match the registered worktree")
    with _remote_config_lock(host, state["config_path"]):
        content = _read_remote_config(host, state["config_path"])
        if content.count(state["block"]) != 1:
            raise ServiceError(
                "whub-owned remote Codex trust entry was modified and was not removed"
            )
        _write_remote_config(
            host,
            state["config_path"],
            _remove_block(content, state["block"]),
        )
    state_path.unlink()


def _remote_config_path(host: Host) -> str:
    result = run_ssh_command(host, 'printf %s "$HOME/.codex/config.toml"')
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise ServiceError(f"failed to resolve remote Codex config: {detail}")
    return result.stdout


def _read_remote_config(host: Host, path: str) -> str:
    exists = run_ssh_command(host, f"test -e {shlex.quote(path)}")
    if exists.returncode == 1:
        return ""
    if exists.returncode != 0:
        detail = exists.stderr.strip() or f"exit status {exists.returncode}"
        raise ServiceError(f"remote Codex trust operation failed: {detail}")
    result = run_ssh_command(host, f"cat -- {shlex.quote(path)}")
    if result.returncode == 0:
        return result.stdout
    detail = result.stderr.strip() or f"exit status {result.returncode}"
    raise ServiceError(f"remote Codex trust operation failed: {detail}")


def _write_remote_config(host: Host, path: str, content: str) -> None:
    if not content:
        result = run_ssh_command(host, f"rm -f -- {shlex.quote(path)}")
    else:
        parent = shlex.quote(str(Path(path).parent))
        mkdir = run_ssh_command(host, f"mkdir -p -- {parent}")
        if mkdir.returncode != 0:
            detail = mkdir.stderr.strip() or f"exit status {mkdir.returncode}"
            raise ServiceError(f"remote Codex trust operation failed: {detail}")
        result = remote_write_file(host, path, content)
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise ServiceError(f"remote Codex trust operation failed: {detail}")


@contextmanager
def _remote_config_lock(host: Host, path: str):
    lock_path = f"{path}.whub-lock"
    parent = shlex.quote(str(Path(path).parent))
    lock = shlex.quote(lock_path)
    acquired = run_ssh_command(
        host,
        (
            f"if ! mkdir -p -- {parent}; then exit 70; fi; "
            "i=0; "
            f"while ! mkdir -- {lock} 2>/dev/null; do "
            f"if test ! -d {lock}; then exit 70; fi; "
            'i=$((i + 1)); if test "$i" -ge 100; then exit 75; fi; '
            "sleep 0.05; "
            "done"
        ),
    )
    if acquired.returncode == 75:
        raise ServiceError(f"remote Codex trust lock timed out: {lock_path}")
    if acquired.returncode != 0:
        detail = acquired.stderr.strip() or f"exit status {acquired.returncode}"
        raise ServiceError(f"remote Codex trust lock failed: {detail}")
    try:
        yield
    finally:
        released = run_ssh_command(host, f"rmdir -- {lock}")
        if released.returncode != 0:
            detail = released.stderr.strip() or f"exit status {released.returncode}"
            raise ServiceError(f"remote Codex trust unlock failed: {detail}")


def _remote_state_path(workspace_root: Path, project: str, task_id: str) -> Path:
    return (
        workspace_root
        / "projects/worktrees/agents"
        / f"{project}-{task_id.removeprefix('TASK-')}.remote-codex-trust.json"
    )


def _load_remote_state(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text())
        if not isinstance(state, dict) or not all(
            isinstance(state.get(key), str)
            for key in ("config_path", "worktree", "block")
        ):
            raise ValueError("invalid fields")
        return state
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ServiceError(f"invalid remote Codex trust state: {path}: {error}") from error


def _save_remote_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, sort_keys=True) + "\n")
