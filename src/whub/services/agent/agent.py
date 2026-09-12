"""Prepare and close Agent worktree sessions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from whub.core.tmux import TmuxSession
from whub.models import Manifest
from whub.services.agent.adapters.claude_code import render as render_claude_code
from whub.services.agent.adapters.codex import render as render_codex
from whub.services.agent.auth import (
    resolve_agent_auth,
    resolve_variables,
)
from whub.services.agent.context import render_context
from whub.services.agent.codex.trust import cleanup as cleanup_codex_trust
from whub.services.agent.codex.trust import cleanup_remote as cleanup_remote_codex_trust
from whub.services.agent.codex.trust import prepare as prepare_codex_trust
from whub.services.agent.codex.trust import prepare_remote as prepare_remote_codex_trust
from whub.services.agent.tmux_session import (
    close_tmux_session,
    list_tmux_sessions,
    open_tmux_session,
)
from whub.services.agent.state import (
    cleanup,
    owned_paths as local_owned_paths,
    prepare,
    unchanged_owned_paths as local_unchanged_owned_paths,
)
from whub.services.agent import remote_state
from whub.services.errors import ServiceError
from whub.services.worktree.resolve import (
    resolve_conventional_worktree,
    resolve_worktree,
)


@dataclass(frozen=True)
class AgentSession:
    """One running Agent tmux session with a valid conventional worktree."""

    project: str
    issue_number: int
    workspace_path: str


def list_agent_sessions(
    manifest: Manifest, workspace_root: Path, project: str
) -> tuple[AgentSession, ...]:
    """List one Project's running Agent sessions; stale tmux sessions are omitted."""
    worktree = resolve_worktree(manifest, workspace_root, project, 1)
    sessions: list[AgentSession] = []
    for issue_number in list_tmux_sessions(project, worktree.host):
        try:
            worktree = resolve_conventional_worktree(
                manifest, workspace_root, project, issue_number
            )
        except (OSError, ServiceError):
            continue
        sessions.append(
            AgentSession(
                worktree.project, worktree.issue_number, worktree.workspace_path
            )
        )
    return tuple(sessions)


def open_agent(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    issue_number: int,
    auth_names: tuple[str, ...],
) -> TmuxSession:
    """Prepare PROJECT/ISSUE_NUMBER and return its tmux session."""
    registered = resolve_conventional_worktree(
        manifest, workspace_root, project, issue_number
    )
    agent_id = str(registered.issue_number)
    resolved_auth = resolve_agent_auth(auth_names)
    variables = resolve_variables(
        resolved_auth.auth.variables,
        project,
        agent_id,
        registered.destination,
    )
    files = {
        **render_codex(resolved_auth.auth, resolved_auth.tools, variables),
        **render_claude_code(resolved_auth.auth, resolved_auth.tools, variables),
    }
    context = render_context(workspace_root, auth_names, registered.branch)
    if registered.host is None:
        assert isinstance(registered.destination, Path)
        prepare(
            workspace_root,
            project,
            agent_id,
            registered.destination,
            files,
            context,
        )
        prepare_codex_trust(
            workspace_root, project, agent_id, registered.destination
        )
        return open_tmux_session(
            project, agent_id, registered.destination, workspace_root
        )

    assert registered.host is not None and isinstance(registered.destination, str)
    prepare_remote_codex_trust(
        workspace_root,
        project,
        agent_id,
        registered.host,
        registered.destination,
    )
    remote_state.prepare(
        workspace_root,
        project,
        agent_id,
        registered.host,
        registered.destination,
        files,
        context,
    )
    return open_tmux_session(
        project,
        agent_id,
        registered.destination,
        workspace_root,
        registered.host,
    )


def generated_paths(
    manifest: Manifest, workspace_root: Path, project: str, issue_number: int
) -> set[PurePosixPath]:
    """Return Agent-owned paths for one registered local or remote worktree."""
    registered = resolve_conventional_worktree(
        manifest, workspace_root, project, issue_number
    )
    if registered.is_remote:
        assert isinstance(registered.destination, str)
        return remote_state.owned_paths(
            workspace_root,
            project,
            str(registered.issue_number),
            registered.destination,
        )
    assert isinstance(registered.destination, Path)
    return local_owned_paths(
        workspace_root,
        project,
        str(registered.issue_number),
        registered.destination,
    )


def unchanged_generated_paths(
    manifest: Manifest, workspace_root: Path, project: str, issue_number: int
) -> set[PurePosixPath]:
    """Return Agent paths safe to ignore in a clean-worktree check."""
    registered = resolve_conventional_worktree(
        manifest, workspace_root, project, issue_number
    )
    if registered.is_remote:
        assert registered.host is not None and isinstance(registered.destination, str)
        return remote_state.unchanged_owned_paths(
            workspace_root,
            project,
            str(registered.issue_number),
            registered.host,
            registered.destination,
        )
    assert isinstance(registered.destination, Path)
    return local_unchanged_owned_paths(
        workspace_root,
        project,
        str(registered.issue_number),
        registered.destination,
    )


def close_agent(
    manifest: Manifest, workspace_root: Path, project: str, issue_number: int
) -> None:
    """Stop PROJECT/ISSUE_NUMBER's session and clean its owned configuration."""
    registered = resolve_conventional_worktree(
        manifest, workspace_root, project, issue_number
    )
    agent_id = str(registered.issue_number)
    if registered.host is None:
        assert isinstance(registered.destination, Path)
        close_tmux_session(project, agent_id)
        cleanup_codex_trust(
            workspace_root, project, agent_id, registered.destination
        )
        cleanup(workspace_root, project, agent_id, registered.destination)
        return

    assert registered.host is not None and isinstance(registered.destination, str)
    close_tmux_session(project, agent_id, registered.host)
    cleanup_remote_codex_trust(
        workspace_root,
        project,
        agent_id,
        registered.host,
        registered.destination,
    )
    remote_state.cleanup(
        workspace_root,
        project,
        agent_id,
        registered.host,
        registered.destination,
    )
