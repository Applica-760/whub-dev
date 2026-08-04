"""CLI commands for registered Git worktrees."""

from __future__ import annotations

import re

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.commands import project_names
from whub.services.errors import ServiceError
from whub.services.worktree import (
    create_project_pull_request,
    create_project_worktree,
    inspect_worktrees,
    merge_project_pull_request,
    remove_project_worktree,
)
from whub.utils.render import render_table
from whub.wflow.models.task import TASK_ID_PATTERN


_TASK_ID_PATTERN = re.compile(TASK_ID_PATTERN)


def _task_id(value: str) -> str:
    if not _TASK_ID_PATTERN.fullmatch(value):
        raise click.BadParameter("expected TASK-NNN", param_hint="task_id")
    return value


@click.group()
def worktree() -> None:
    """Create, inspect, and remove registered Git worktrees."""


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument("task_id", callback=lambda _ctx, _param, value: _task_id(value))
@click.pass_context
def create(ctx: click.Context, project: str, task_id: str) -> None:
    """Create PROJECT's worktree for TASK_ID."""
    workspace_root = current_context().workspace_root
    try:
        destination = create_project_worktree(
            get_manifest(ctx), workspace_root, project, task_id
        )
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    number = task_id.removeprefix("TASK-")
    render_table(
        [(project, task_id, f"tasks/{number}", destination)],
        headers=("project", "task", "branch", "workspace path"),
    )


@worktree.command(name="pull-request")
@click.argument("project", shell_complete=project_names)
@click.argument("task_id", callback=lambda _ctx, _param, value: _task_id(value))
@click.pass_context
def pull_request(ctx: click.Context, project: str, task_id: str) -> None:
    """Create or show PROJECT's pull request for TASK_ID."""
    workspace_root = current_context().workspace_root
    try:
        url = create_project_pull_request(
            get_manifest(ctx), workspace_root, project, task_id
        )
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"pull request {project}/{task_id}: {url}")


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument("task_id", callback=lambda _ctx, _param, value: _task_id(value))
@click.option(
    "--method",
    type=click.Choice(("merge", "squash", "rebase")),
    required=True,
    help="GitHub merge method.",
)
@click.pass_context
def merge(ctx: click.Context, project: str, task_id: str, method: str) -> None:
    """Merge PROJECT's pull request for TASK_ID and remove its worktree."""
    workspace_root = current_context().workspace_root
    try:
        merge_project_pull_request(
            get_manifest(ctx), workspace_root, project, task_id, method
        )
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"merged {project}/{task_id}")


@worktree.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Inspect all registered worktrees without changing them."""
    workspace_root = current_context().workspace_root
    try:
        inspections = inspect_worktrees(get_manifest(ctx), workspace_root)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    if not inspections:
        click.echo("(no worktrees)")
        return
    rows = []
    unhealthy = False
    for inspection in inspections:
        definition = inspection.definition
        diagnostics = "; ".join(inspection.diagnostics) or "ok"
        unhealthy = unhealthy or bool(inspection.diagnostics)
        rows.append(
            (
                definition.parent_project if definition else "-",
                definition.task_id if definition else "-",
                definition.branch if definition else "-",
                definition.workspace_path if definition else "-",
                diagnostics,
            )
        )
    render_table(
        rows,
        headers=("project", "task", "branch", "workspace path", "diagnostic"),
    )
    if unhealthy:
        raise click.exceptions.Exit(1)


@worktree.command()
@click.argument("project", shell_complete=project_names)
@click.argument("task_id", callback=lambda _ctx, _param, value: _task_id(value))
@click.pass_context
def remove(ctx: click.Context, project: str, task_id: str) -> None:
    """Remove PROJECT's clean worktree for TASK_ID."""
    workspace_root = current_context().workspace_root
    try:
        remove_project_worktree(get_manifest(ctx), workspace_root, project, task_id)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"removed {project}/{task_id}")
