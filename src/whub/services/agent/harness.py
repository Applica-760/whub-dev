"""Prepare one registered worktree for a Codex Agent session."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
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
from whub.services.errors import ServiceError
from whub.services.worktree.operation import resolve_project_worktree


@dataclass(frozen=True)
class _PreparedHarness:
    """One worktree and its generated Agent configuration files."""

    project: str
    task_id: str
    worktree: Path
    files: tuple[Path, ...]


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
        resolved_auth.auth.variables, project, registered.task_id, registered.destination
    )
    plans = (
        render_codex(resolved_auth.auth, resolved_auth.tools, variables),
        render_claude_code(resolved_auth.auth, resolved_auth.tools, variables),
    )
    files = tuple(
        path for plan in plans for path in _materialize(registered.destination, plan.files)
    )
    harness = _PreparedHarness(project, registered.task_id, registered.destination, files)
    return _start_tmux_session(harness, workspace_root)


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


def _materialize(
    worktree: Path, files: Mapping[PurePosixPath, str]
) -> tuple[Path, ...]:
    paths = []
    for relative, content in files.items():
        target = _safe_target(worktree, relative)
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise ServiceError(
                    f"generated config path is not a regular file: {relative}"
                )
            if target.read_text() != content:
                raise ServiceError(f"generated config already exists: {relative}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_text(content, encoding="utf-8", newline="\n")
            except OSError as error:
                raise ServiceError(
                    f"failed to write generated config: {relative}: {error}"
                ) from error
        paths.append(target)
    return tuple(paths)


def _safe_target(worktree: Path, relative: PurePosixPath) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ServiceError(f"invalid generated config path: {relative}")
    parent = worktree
    for part in relative.parts[:-1]:
        parent = parent / part
        if parent.is_symlink():
            raise ServiceError(f"generated config parent is a symlink: {relative}")
        if parent.exists() and not parent.is_dir():
            raise ServiceError(
                f"generated config parent is not a directory: {relative}"
            )
    return worktree.joinpath(*relative.parts)
