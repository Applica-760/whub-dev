"""Prepare and close Agent worktree sessions."""

from __future__ import annotations

from pathlib import Path

from whub.core.target import TargetItem, TargetError, on_targets, resolve_project_resource
from whub.core.tmux import TmuxSession
from whub.models import Manifest, RemoteResource, SymlinkResource
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
    open_tmux_session,
)
from whub.services.agent.state import cleanup, prepare
from whub.services.agent import remote_state
from whub.services.errors import ServiceError
from whub.services.worktree.resolve import (
    ResolvedProjectWorktree,
    resolve_project_worktree,
)


def open_agent(
    manifest: Manifest,
    workspace_root: Path,
    project: str,
    task_id: str,
    auth_names: tuple[str, ...],
) -> TmuxSession:
    """Prepare PROJECT/TASK and return its tmux session."""
    registered = resolve_project_worktree(manifest, workspace_root, project, task_id)
    resolved_auth = resolve_agent_auth(auth_names)
    variables = resolve_variables(
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
    context = render_context(workspace_root, auth_names, registered.definition.branch)
    try:
        resource = resolve_project_resource(manifest, project)
    except TargetError as error:
        raise ServiceError(str(error)) from error

    def local(_: SymlinkResource, item: ResolvedProjectWorktree) -> TmuxSession:
        assert isinstance(item.destination, Path)
        prepare(
            workspace_root,
            project,
            item.definition.task_id,
            item.destination,
            files,
            context,
        )
        prepare_codex_trust(
            workspace_root, project, item.definition.task_id, item.destination
        )
        return open_tmux_session(
            project, item.definition.task_id, item.destination, workspace_root
        )

    def remote(_: RemoteResource, item: ResolvedProjectWorktree) -> TmuxSession:
        assert item.host is not None and isinstance(item.destination, str)
        prepare_remote_codex_trust(
            workspace_root,
            project,
            item.definition.task_id,
            item.host,
            item.destination,
        )
        remote_state.prepare(
            workspace_root,
            project,
            item.definition.task_id,
            item.host,
            item.destination,
            files,
            context,
        )
        return open_tmux_session(
            project,
            item.definition.task_id,
            item.destination,
            workspace_root,
            item.host,
        )

    return on_targets(
        [TargetItem(resource, registered)], local=local, remote=remote
    )[0]


def close_agent(
    manifest: Manifest, workspace_root: Path, project: str, task_id: str
) -> None:
    """Stop PROJECT/TASK's session and clean its owned configuration."""
    registered = resolve_project_worktree(manifest, workspace_root, project, task_id)
    try:
        resource = resolve_project_resource(manifest, project)
    except TargetError as error:
        raise ServiceError(str(error)) from error

    def local(_: SymlinkResource, item: ResolvedProjectWorktree) -> None:
        assert isinstance(item.destination, Path)
        close_tmux_session(project, item.definition.task_id)
        cleanup_codex_trust(
            workspace_root, project, item.definition.task_id, item.destination
        )
        cleanup(workspace_root, project, item.definition.task_id, item.destination)

    def remote(_: RemoteResource, item: ResolvedProjectWorktree) -> None:
        assert item.host is not None and isinstance(item.destination, str)
        close_tmux_session(project, item.definition.task_id, item.host)
        cleanup_remote_codex_trust(
            workspace_root,
            project,
            item.definition.task_id,
            item.host,
            item.destination,
        )
        remote_state.cleanup(
            workspace_root,
            project,
            item.definition.task_id,
            item.host,
            item.destination,
        )

    on_targets([TargetItem(resource, registered)], local=local, remote=remote)
