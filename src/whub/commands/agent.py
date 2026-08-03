"""Open prepared Agent worktree shells."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.models import project_names
from whub.services.agent.agent import close_agent, open_agent
from whub.services.errors import ServiceError
from whub.webapp.agent_attention_control import submit as submit_attention_hook
from whub.webapp.agent_codex_control import start as start_app_server
from whub.webapp.agent_codex_control import stop as stop_app_server


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
    context = current_context()
    try:
        session = open_agent(
            get_manifest(ctx),
            context.workspace_root,
            project,
            task,
            auth_names,
        )
        start_app_server(context, project, task)
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    os.execvp(session.attach_command[0], list(session.attach_command))


@agent.command()
@click.argument("project", shell_complete=project_names)
@click.argument("task")
@click.pass_context
def close(ctx: click.Context, project: str, task: str) -> None:
    """Stop PROJECT/TASK's Agent shell and remove owned configuration."""
    context = current_context()
    control_error: ServiceError | None = None
    try:
        try:
            stop_app_server(context, project, task)
        except ServiceError as error:
            control_error = error
        close_agent(
            get_manifest(ctx), context.workspace_root, project, task
        )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    if control_error is not None:
        raise click.ClickException(str(control_error))
    click.echo(f"closed {project}/{task}")


@agent.command(name="attention-hook")
def attention_hook() -> None:
    """Forward one Codex Hook event without affecting its approval flow."""
    try:
        event = json.load(click.get_text_stream("stdin"))
        if not isinstance(event, Mapping):
            return
        submit_attention_hook(current_context(), event)
    except (OSError, ServiceError, TypeError, json.JSONDecodeError):
        return
