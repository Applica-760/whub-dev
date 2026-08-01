"""tmux lifecycle for one Agent worktree session."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess

from whub.core.tmux import session_name, session_target, tmux_command
from whub.services.errors import ServiceError


@dataclass(frozen=True)
class TmuxSession:
    """One running or resumable tmux session for an Agent worktree."""

    name: str
    attach_command: tuple[str, ...]


def open_tmux_session(
    project: str, task_id: str, worktree: Path, workspace_root: Path
) -> TmuxSession:
    """Return an existing Agent tmux session or start one in WORKTREE."""
    name = session_name(project, task_id)
    target = session_target(name)
    attach_command = tuple(tmux_command("attach-session", "-t", target))
    try:
        existing = subprocess.run(
            tmux_command("has-session", "-t", target), capture_output=True, text=True
        )
    except OSError as error:
        raise ServiceError(f"tmux is unavailable: {error}") from error
    if existing.returncode == 0:
        return TmuxSession(name, attach_command)

    command = f"cd {shlex.quote(str(worktree))} && exec $SHELL -l"
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
    return TmuxSession(name, attach_command)


def close_tmux_session(project: str, task_id: str) -> None:
    """Stop one Agent tmux session when it exists."""
    target = session_target(session_name(project, task_id))
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
