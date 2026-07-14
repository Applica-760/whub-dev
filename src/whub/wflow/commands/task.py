"""Commands for task execution records."""
from __future__ import annotations

import click

from pathlib import Path

from whub.wflow.services import (
    WflowError,
    check_task,
    load_task,
    load_task_workflow,
)


@click.group()
def task() -> None:
    """Operate task execution records."""


@task.command()
@click.argument("task_path", type=click.Path(path_type=Path))
def check(task_path: Path) -> None:
    """Check one task execution record."""
    try:
        diagnostics = check_task(load_task(task_path), load_task_workflow())
    except WflowError as error:
        raise click.ClickException(str(error)) from error

    if not diagnostics:
        click.echo(f"valid {task_path}")
        return
    for diagnostic in diagnostics:
        click.echo(f"{diagnostic.code}: {diagnostic.message}", err=True)
    raise click.exceptions.Exit(1)
