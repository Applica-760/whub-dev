"""Prepare one registered worktree for a Codex Agent session."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess

from whub.core.tmux import session_name, session_target, tmux_command
from whub.models import Manifest
from whub.models.agent.auth import (
    RegisteredProjectVariable,
    RegisteredTaskWorktreeVariable,
)
from whub.services.agent.adapters.claude_code import render as render_claude_code
from whub.services.agent.adapters.codex import render as render_codex
from whub.services.agent.auth import resolve_agent_auth
from whub.services.agent.state import cleanup, prepare
from whub.services.errors import ServiceError
from whub.services.worktree.operation import resolve_project_worktree


@dataclass(frozen=True)
class _PreparedHarness:
    """One worktree prepared for an Agent harness session."""

    project: str
    task_id: str
    worktree: Path


@dataclass(frozen=True)
class HarnessSession:
    """One running or resumable tmux session for a prepared Agent harness."""

    name: str
    attach_command: tuple[str, ...]


def open_harness(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
    auth_names: tuple[str, ...],
) -> HarnessSession:
    """Open PROJECT/TASK's configured Agent worktree shell."""
    registered = resolve_project_worktree(manifest, workspace_root, project, task_id)
    resolved_auth = resolve_agent_auth(auth_names)
    variables = _resolve_variables(
        resolved_auth.auth.variables,
        project,
        registered.definition.task_id,
        registered.destination,
    )
    plans = (
        render_codex(resolved_auth.auth, resolved_auth.tools, variables),
        render_claude_code(resolved_auth.auth, resolved_auth.tools, variables),
    )
    files = {
        relative: content for plan in plans for relative, content in plan.files.items()
    }
    prepare(
        workspace_root,
        project,
        registered.definition.task_id,
        registered.destination,
        files,
    )
    harness = _PreparedHarness(
        project, registered.definition.task_id, registered.destination
    )
    return _start_tmux_session(harness, workspace_root)


def close_harness(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> None:
    """Stop one harness session and clean its owned generated files."""
    registered = resolve_project_worktree(manifest, workspace_root, project, task_id)
    _stop_tmux_session(session_name(project, registered.definition.task_id))
    cleanup(
        workspace_root, project, registered.definition.task_id, registered.destination
    )


def _start_tmux_session(
    harness: _PreparedHarness, workspace_root: Path
) -> HarnessSession:
    name = session_name(harness.project, harness.task_id)
    target = session_target(name)
    attach_command = tuple(tmux_command("attach-session", "-t", target))
    try:
        existing = subprocess.run(
            tmux_command("has-session", "-t", target), capture_output=True, text=True
        )
    except OSError as error:
        raise ServiceError(f"tmux is unavailable: {error}") from error
    if existing.returncode == 0:
        return HarnessSession(name, attach_command)

    command = f"cd {shlex.quote(str(harness.worktree))} && exec $SHELL -l"
    try:
        created = subprocess.run(
            tmux_command(
                "new-session",
                "-d",
                "-s",
                name,
                "-c",
                str(workspace_root),
                command,
            ),
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ServiceError(f"failed to start tmux: {error}") from error
    if created.returncode != 0:
        detail = created.stderr.strip() or f"exit status {created.returncode}"
        raise ServiceError(f"failed to start tmux: {detail}")
    return HarnessSession(name, attach_command)


def _stop_tmux_session(name: str) -> None:
    target = session_target(name)
    try:
        existing = subprocess.run(
            tmux_command("has-session", "-t", target), capture_output=True, text=True
        )
    except OSError as error:
        raise ServiceError(f"tmux is unavailable: {error}") from error
    if existing.returncode != 0:
        return
    stopped = subprocess.run(
        tmux_command("kill-session", "-t", target), capture_output=True, text=True
    )
    if stopped.returncode != 0:
        detail = stopped.stderr.strip() or f"exit status {stopped.returncode}"
        raise ServiceError(f"failed to stop tmux session: {detail}")


def _resolve_variables(
    definitions: dict,
    project: str,
    task_id: str,
    worktree: Path,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, definition in definitions.items():
        if isinstance(definition, RegisteredProjectVariable):
            values[name] = project
        elif isinstance(definition, RegisteredTaskWorktreeVariable):
            available = {"project": project, "task": task_id, "path": str(worktree)}
            values.update(
                {f"{name}.{field}": available[field] for field in definition.fields}
            )
        else:
            raise ServiceError(f"unsupported Agent auth variable: {name}")
    return values
