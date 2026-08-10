"""CLI commands for minimal Task runtime operations."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from whub.commands import get_manifest, project_names
from whub.services.errors import ServiceError
from whub.services.flow.errors import FlowError
from whub.services.task import application
from whub.services.task.common import create_task
from whub.services.task.log import append_task_log
from whub.services.task.query import load_task_records
from whub.services.task_resolution import resolve_project_task_storage


def _invoke(operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return operation(*args, **kwargs)
    except (FlowError, OSError, ServiceError) as error:
        raise click.ClickException(str(error)) from error


def _storage() -> tuple[Path, Path, tuple[Path, ...], tuple[Path, ...]]:
    storage = _invoke(
        resolve_project_task_storage,
        get_manifest(click.get_current_context()),
        _project(),
    )
    storage.active_root.mkdir(parents=True, exist_ok=True)
    roots = tuple(root for root in storage.read_roots if root != storage.active_root)
    return storage.active_root, storage.archive_root, roots, storage.id_roots


def _project() -> str:
    return click.get_current_context().meta["task_project"]


def _task_id(reference: str) -> str:
    if reference.startswith("TASK-"):
        return reference
    if reference.isdecimal():
        return f"TASK-{reference}"
    raise click.BadParameter("expected TASK-NNN or NNN", param_hint="task_ref")


@click.group()
@click.option(
    "--project", required=True, shell_complete=project_names, help="Target Project."
)
@click.pass_context
def task(ctx: click.Context, project: str) -> None:
    """Operate minimal Task runtime records."""
    ctx.meta["task_project"] = project


@task.command("init")
@click.argument("title")
@click.argument("objective")
@click.option("--approach", "approaches", multiple=True, help="Add one approach.")
def init(title: str, objective: str, approaches: tuple[str, ...]) -> None:
    """Create a draft Task YAML and Markdown pair."""
    active_root, _, _, id_roots = _storage()
    path, record = _invoke(
        create_task, active_root, title, objective, approaches, id_roots=id_roots
    )
    click.echo(f"initialized {record.id}: {path}")


@task.command()
@click.argument("task_ref")
def check(task_ref: str) -> None:
    """Validate TASK_REF across active and archive storage."""
    active_root, _, read_roots, _ = _storage()
    records = _invoke(load_task_records, active_root, *read_roots)
    task_id = _task_id(task_ref)
    if task_id not in records:
        raise click.ClickException(f"task ID not found: {task_id}")
    click.echo(f"valid {records[task_id][0]}")


@task.command("start")
@click.argument("task_ref")
def start(task_ref: str) -> None:
    """Start a draft Task whose dependencies are complete."""
    active_root, _, read_roots, _ = _storage()
    updated = _invoke(application.start_task, active_root, task_ref, *read_roots)
    click.echo(f"started {updated.id}")


@task.group("depends")
def depends() -> None:
    """Edit Task dependencies."""


@depends.command("add")
@click.argument("task_ref")
@click.argument("dependency")
def add_dependency(task_ref: str, dependency: str) -> None:
    """Add one dependency."""
    active_root, _, read_roots, _ = _storage()
    _invoke(
        application.update_dependency_for_task,
        active_root,
        task_ref,
        dependency,
        True,
        *read_roots,
    )
    click.echo(f"added dependency {dependency}")


@depends.command("delete")
@click.argument("task_ref")
@click.argument("dependency")
def delete_dependency(task_ref: str, dependency: str) -> None:
    """Delete one dependency."""
    active_root, _, read_roots, _ = _storage()
    _invoke(
        application.update_dependency_for_task,
        active_root,
        task_ref,
        dependency,
        False,
        *read_roots,
    )
    click.echo(f"deleted dependency {dependency}")


@task.command()
@click.argument("parent_ref")
@click.argument("child_ref")
@click.option("--reason", required=True, help="Why the parent is interrupted.")
def interrupt(parent_ref: str, child_ref: str, reason: str) -> None:
    """Pause PARENT_REF and start CHILD_REF."""
    active_root, _, read_roots, _ = _storage()
    parent, child = _invoke(
        application.interrupt, active_root, parent_ref, child_ref, reason, *read_roots
    )
    click.echo(f"interrupted {parent.id} with {child.id}")


@task.command()
@click.argument("parent_ref")
def resume(parent_ref: str) -> None:
    """Resume a paused Task after its interruption Task is terminal."""
    active_root, _, read_roots, _ = _storage()
    updated = _invoke(application.resume, active_root, parent_ref, *read_roots)
    click.echo(f"resumed {updated.id}")


@task.command("complete")
@click.argument("task_ref")
def complete(task_ref: str) -> None:
    """Complete and archive TASK_REF."""
    active_root, archive_root, read_roots, _ = _storage()
    destination = _invoke(
        application.complete_task, active_root, archive_root, task_ref, *read_roots
    )
    click.echo(f"completed {_task_id(task_ref)}: {destination}")


@task.command("cancel")
@click.argument("task_ref")
@click.option("--reason", required=True, help="Why the Task is cancelled.")
def cancel(task_ref: str, reason: str) -> None:
    """Cancel and archive TASK_REF."""
    active_root, archive_root, read_roots, _ = _storage()
    destination = _invoke(
        application.cancel_task,
        active_root,
        archive_root,
        task_ref,
        reason,
        *read_roots,
    )
    click.echo(f"cancelled {_task_id(task_ref)}: {destination}")


@task.command("log")
@click.argument("task_ref")
@click.option(
    "--log",
    "payload",
    required=True,
    help='One JSON LogKind entry, e.g. {"fact":"observed"}.',
)
def log(task_ref: str, payload: str) -> None:
    """Append one structured Task Markdown log entry."""
    active_root, _, read_roots, _ = _storage()
    records = _invoke(load_task_records, active_root, *read_roots)
    task_id = _task_id(task_ref)
    if task_id not in records:
        raise click.ClickException(f"task ID not found: {task_id}")
    path, _ = records[task_id]
    if not path.is_relative_to(active_root):
        raise click.ClickException(f"task is archived: {task_id}")
    _invoke(append_task_log, path, payload)
    click.echo(f"logged {task_id}")
