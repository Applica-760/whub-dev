"""Manage tmux lifecycle for one Agent worktree session."""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from whub.core.remote import build_ssh_command, run_ssh_command
from whub.core.tmux import TmuxSession, session_name, session_target, tmux_command
from whub.models import Host
from whub.services.errors import ServiceError


def resolve_tmux_session(project: str, task_id: str) -> TmuxSession:
    """Return an existing Agent tmux session without creating one."""
    name = session_name(project, task_id)
    target = session_target(name)
    try:
        result = subprocess.run(
            tmux_command("has-session", "-t", target), capture_output=True, text=True
        )
    except OSError as error:
        raise ServiceError(f"tmux is unavailable: {error}") from error
    if result.returncode:
        raise ServiceError(f"Agent tmux session is unavailable: {project}/{task_id}")
    return TmuxSession(name, tuple(tmux_command("attach-session", "-t", target)))


def open_tmux_session(
    project: str,
    task_id: str,
    worktree: Path | str,
    workspace_root: Path,
    host: Host | None = None,
) -> TmuxSession:
    """Return an existing Agent tmux session or start one in WORKTREE."""
    name = session_name(project, task_id)
    target = session_target(name)
    if host is not None:
        assert isinstance(worktree, str)
        command = _shell_command(worktree)
        if not _remote_session_exists(host, target):
            created = run_ssh_command(
                host,
                f"tmux new-session -d -s {name} -c {shlex.quote(worktree)} {shlex.quote(command)}",
            )
            if created.returncode != 0:
                detail = created.stderr.strip() or f"exit status {created.returncode}"
                raise ServiceError(f"failed to start remote tmux: {detail}")
        return TmuxSession(
            name,
            tuple(build_ssh_command(host, f"exec tmux attach-session -t {target}", tty=True)),
        )

    assert isinstance(worktree, Path)
    attach_command = tuple(tmux_command("attach-session", "-t", target))
    try:
        existing = subprocess.run(
            tmux_command("has-session", "-t", target), capture_output=True, text=True
        )
    except OSError as error:
        raise ServiceError(f"tmux is unavailable: {error}") from error
    if existing.returncode == 0:
        return TmuxSession(name, attach_command)

    command = _shell_command(str(worktree))
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


def _shell_command(worktree: str) -> str:
    return (
        f"cd {shlex.quote(worktree)} && "
        "printf '%s\\n' 'whub: use the Web Agent panel to start Codex; "
        "this tmux session remains available for general shell commands.' && "
        "exec $SHELL -l"
    )


def close_tmux_session(project: str, task_id: str, host: Host | None = None) -> None:
    """Stop one Agent tmux session when it exists."""
    target = session_target(session_name(project, task_id))
    if host is not None:
        if _remote_session_exists(host, target):
            stopped = run_ssh_command(host, f"tmux kill-session -t {target}")
            if stopped.returncode != 0:
                detail = stopped.stderr.strip() or f"exit status {stopped.returncode}"
                raise ServiceError(f"failed to stop remote tmux: {detail}")
        return
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


def _remote_session_exists(host: Host, target: str) -> bool:
    result = run_ssh_command(host, f"tmux has-session -t {target}")
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = result.stderr.strip() or f"exit status {result.returncode}"
    raise ServiceError(f"failed to inspect remote tmux: {detail}")
