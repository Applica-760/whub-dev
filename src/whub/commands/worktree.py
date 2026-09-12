"""Open and merge conventional Task worktrees."""

from __future__ import annotations

import os

import click

from whub.commands import get_manifest, project_names
from whub.core.context import current_context
from whub.services.errors import ServiceError
from whub.services.worktree.operation import (
    close_project_worktree,
    create_project_pull_request,
    open_project_worktree,
)


@click.group()
def worktree() -> None:
    """Open and close conventional Issue worktrees."""


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument("issue_number", metavar="ISSUE_NUMBER", type=click.IntRange(min=1))
@click.option("--auth", "auth_names", multiple=True, required=True)
@click.pass_context
def open(
    ctx: click.Context, project: str, issue_number: int, auth_names: tuple[str, ...]
) -> None:
    """Create PROJECT/ISSUE_NUMBER, prepare its Agent, and attach tmux."""
    context = current_context()
    try:
        session = open_project_worktree(
            get_manifest(ctx), context.workspace_root, project, issue_number, auth_names
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    os.execvp(session.attach_command[0], list(session.attach_command))


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument("issue_number", metavar="ISSUE_NUMBER", type=click.IntRange(min=1))
@click.pass_context
def close(ctx: click.Context, project: str, issue_number: int) -> None:
    """Clean Agent files, merge PROJECT/ISSUE_NUMBER, then remove its worktree."""
    context = current_context()
    try:
        url = close_project_worktree(
            get_manifest(ctx), context.workspace_root, project, issue_number
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"merged {project}/{issue_number}: {url}")


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument("issue_number", metavar="ISSUE_NUMBER", type=click.IntRange(min=1))
@click.pass_context
def pr(ctx: click.Context, project: str, issue_number: int) -> None:
    """Push PROJECT/ISSUE_NUMBER and create or return its pull request."""
    context = current_context()
    try:
        url = create_project_pull_request(
            get_manifest(ctx), context.workspace_root, project, issue_number
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"pull request {project}/{issue_number}: {url}")
