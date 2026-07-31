"""Open prepared Agent worktree shells."""

from __future__ import annotations

from importlib.resources import as_file, files
import os
from pathlib import Path

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.models import load_agent_auth, load_extension_tool, project_names
from whub.services.agent.harness import open_harness
from whub.services.errors import ServiceError

@click.group()
def agent() -> None:
    """Open Agent worktree shells."""


@agent.command()
@click.argument("project", shell_complete=project_names)
@click.argument("task")
@click.option("--auth", "auth_names", multiple=True, required=True)
@click.pass_context
def open(ctx: click.Context, project: str, task: str, auth_names: tuple[str, ...]) -> None:
    """Prepare PROJECT/TASK and attach its Agent shell."""
    try:
        if any(Path(name).name != name for name in auth_names):
            raise ServiceError("invalid Agent auth name")
        with as_file(files("whub").joinpath("assets")) as assets:
            extensions = tuple(
                load_agent_auth(assets / "roles" / name / "agent-auth.yaml")
                for name in auth_names
            )
            session = open_harness(
                get_manifest(ctx),
                current_context().workspace_root,
                project,
                task,
                load_agent_auth(assets / "roles" / "base.yaml"),
                extensions,
                load_extension_tool(assets / "extension_tools"),
            )
    except (OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    os.execvp(session.attach_command[0], list(session.attach_command))
