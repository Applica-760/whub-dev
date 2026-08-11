"""Open and merge conventional Task worktrees."""

from __future__ import annotations

import os
import re

import click

from whub.commands import get_manifest, project_names
from whub.core.context import current_context
from whub.models.flow import TASK_ID_PATTERN
from whub.services.errors import ServiceError
from whub.services.worktree.operation import (
    close_project_worktree,
    create_project_pull_request,
    open_project_worktree,
)


_TASK_ID_PATTERN = re.compile(TASK_ID_PATTERN)


def _task_id(value: str) -> str:
    task_id = f"TASK-{value}"
    if not _TASK_ID_PATTERN.fullmatch(task_id):
        raise click.BadParameter("expected TTT", param_hint="task_id")
    return task_id


@click.group()
def worktree() -> None:
    """Open and close conventional Task worktrees."""


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument(
    "task_id", metavar="TTT", callback=lambda _ctx, _param, value: _task_id(value)
)
@click.option("--auth", "auth_names", multiple=True, required=True)
@click.pass_context
def open(
    ctx: click.Context, project: str, task_id: str, auth_names: tuple[str, ...]
) -> None:
    """Create PROJECT/TTT, prepare its Agent, and attach tmux."""
    context = current_context()
    try:
        session = open_project_worktree(
            get_manifest(ctx), context.workspace_root, project, task_id, auth_names
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    os.execvp(session.attach_command[0], list(session.attach_command))


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument(
    "task_id", metavar="TTT", callback=lambda _ctx, _param, value: _task_id(value)
)
@click.pass_context
def close(ctx: click.Context, project: str, task_id: str) -> None:
    """Clean Agent files, merge PROJECT/TTT, then remove its worktree."""
    context = current_context()
    try:
        url = close_project_worktree(
            get_manifest(ctx), context.workspace_root, project, task_id
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"merged {project}/{task_id}: {url}")


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument(
    "task_id", metavar="TTT", callback=lambda _ctx, _param, value: _task_id(value)
)
@click.pass_context
def pr(ctx: click.Context, project: str, task_id: str) -> None:
    """Push PROJECT/TTT and create or return its pull request."""
    context = current_context()
    try:
        url = create_project_pull_request(
            get_manifest(ctx), context.workspace_root, project, task_id
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"pull request {project}/{task_id}: {url}")
