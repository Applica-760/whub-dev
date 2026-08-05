"""SSH-backed Codex trust lifecycle for remote Agent worktrees."""

from __future__ import annotations

import json
from pathlib import Path
import shlex

from whub.core.remote import remote_write_file, run_ssh_command
from whub.models import Host
from whub.services.agent.codex.trust import _append_block, _block, _project_config, _remove_block
from whub.services.errors import ServiceError


def prepare(
    workspace_root: Path, project: str, task_id: str, host: Host, worktree: str
) -> None:
    """Trust a remote worktree and record only the Hub-owned config block."""
    state_path = _state_path(workspace_root, project, task_id)
    existing = _load(state_path)
    if existing is not None:
        if existing["worktree"] != worktree:
            raise ServiceError("remote Codex trust state does not match the registered worktree")
        if _read(host, existing["config_path"]).count(existing["block"]) != 1:
            raise ServiceError("whub-owned remote Codex trust entry was modified")
        return
    config_path = _config_path(host)
    content = _read(host, config_path)
    project_config = _project_config(content, Path(worktree))
    if project_config is not None:
        if project_config.get("trust_level") == "trusted":
            return
        raise ServiceError(f"Codex project trust already exists for: {worktree}")
    block = _block(Path(worktree))
    _write(host, config_path, _append_block(content, block))
    _save(state_path, {"config_path": config_path, "worktree": worktree, "block": block})


def cleanup(
    workspace_root: Path, project: str, task_id: str, host: Host, worktree: str
) -> None:
    """Remove only the unchanged remote Codex trust entry created by whub."""
    state_path = _state_path(workspace_root, project, task_id)
    state = _load(state_path)
    if state is None:
        return
    if state["worktree"] != worktree:
        raise ServiceError("remote Codex trust state does not match the registered worktree")
    content = _read(host, state["config_path"])
    if content.count(state["block"]) != 1:
        raise ServiceError("whub-owned remote Codex trust entry was modified and was not removed")
    _write(host, state["config_path"], _remove_block(content, state["block"]))
    state_path.unlink()


def _config_path(host: Host) -> str:
    result = run_ssh_command(host, 'printf %s "$HOME/.codex/config.toml"')
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise ServiceError(f"failed to resolve remote Codex config: {detail}")
    return result.stdout


def _read(host: Host, path: str) -> str:
    result = run_ssh_command(host, f"cat -- {shlex.quote(path)}")
    if result.returncode == 0:
        return result.stdout
    if "No such file" in result.stderr:
        return ""
    detail = result.stderr.strip() or f"exit status {result.returncode}"
    raise ServiceError(f"remote Codex trust operation failed: {detail}")


def _write(host: Host, path: str, content: str) -> None:
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


def _state_path(workspace_root: Path, project: str, task_id: str) -> Path:
    return workspace_root / "projects/worktrees/agents" / f"{project}-{task_id.removeprefix('TASK-')}.remote-codex-trust.json"


def _load(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text())
        if not isinstance(state, dict) or not all(isinstance(state.get(key), str) for key in ("config_path", "worktree", "block")):
            raise ValueError("invalid fields")
        return state
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ServiceError(f"invalid remote Codex trust state: {path}: {error}") from error


def _save(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, sort_keys=True) + "\n")
