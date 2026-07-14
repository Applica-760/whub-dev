"""Commands for Workflow definitions."""
from __future__ import annotations

from pathlib import Path

import click

from whub.wflow.services import (
    WorkflowError,
    check_workflow,
    load_task_workflow,
    load_workflow,
)


@click.command()
@click.argument("workflow", required=False, type=click.Path(path_type=Path))
def check(workflow: Path | None) -> None:
    """Check a Workflow definition, or the built-in task Workflow."""
    try:
        loaded = load_workflow(workflow) if workflow else load_task_workflow()
    except WorkflowError as error:
        raise click.ClickException(str(error)) from error

    diagnostics = check_workflow(loaded)
    if not diagnostics:
        click.echo(f"valid {loaded.workflow.id}: {loaded.workflow.name}")
        return
    for diagnostic in diagnostics:
        click.echo(f"{diagnostic.code}: {diagnostic.message}", err=True)
    raise click.exceptions.Exit(1)
