"""Open prepared Agent worktree shells."""

from __future__ import annotations

import os

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.models import project_names
from whub.services.agent.harness import close_harness, open_harness
from whub.services.errors import ServiceError


@click.group()
def agent() -> None:
    """Open Agent worktree shells."""


@agent.command()
@click.argument("project", shell_complete=project_names)
@click.argument("task")
@click.option("--auth", "auth_names", multiple=True, required=True)
@click.pass_context
def open(
    ctx: click.Context, project: str, task: str, auth_names: tuple[str, ...]
) -> None:
    """Prepare PROJECT/TASK and attach its Agent shell."""
    try:
        session = open_harness(
            get_manifest(ctx),
            current_context().workspace_root,
            project,
            task,
            auth_names,
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    os.execvp(session.attach_command[0], list(session.attach_command))


@agent.command()
@click.argument("project", shell_complete=project_names)
@click.argument("task")
@click.pass_context
def close(ctx: click.Context, project: str, task: str) -> None:
    """Stop PROJECT/TASK's Agent shell and remove owned configuration."""
    try:
        close_harness(
            get_manifest(ctx), current_context().workspace_root, project, task
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"closed {project}/{task}")
