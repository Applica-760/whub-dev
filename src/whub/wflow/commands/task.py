"""Commands for task execution records."""
from __future__ import annotations

import click

from pathlib import Path

from whub.wflow.services import (
    WflowError,
    apply_transition,
    available_transitions,
    check_task,
    load_task,
    load_task_workflow,
    update_step,
    write_task,
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


@task.command()
@click.argument("task_path", type=click.Path(path_type=Path))
def show(task_path: Path) -> None:
    """Show task state, next Step, and ready transitions."""
    try:
        record = load_task(task_path)
        workflow = load_task_workflow()
        diagnostics = check_task(record, workflow)
        if diagnostics:
            raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))
        steps = (
            [step for phase in record.plan.phases for step in phase.steps]
            if record.plan is not None
            else []
        )
        next_step = next(
            (step for step in steps if step.state not in {"done", "skipped"}), None
        )
        click.echo(f"state: {record.task.state}")
        click.echo(f"next step: {next_step.id if next_step else '-'}")
        transitions = available_transitions(record, workflow)
        click.echo(f"ready transitions: {', '.join(transitions) if transitions else '-'}")
    except WflowError as error:
        raise click.ClickException(str(error)) from error


@task.command("apply")
@click.argument("task_path", type=click.Path(path_type=Path))
@click.argument("trigger")
@click.option("--actor", required=True, help="Workflow role performing the trigger.")
@click.option("--reason", help="Reason for a plan change or cancellation.")
@click.option("--result", help="Summary recorded when completing a task.")
def apply(task_path: Path, trigger: str, actor: str, reason: str | None, result: str | None) -> None:
    """Apply one declared Workflow trigger."""
    input_data = {
        key: value
        for key, value in {"reason": reason, "result": result}.items()
        if value is not None
    }
    try:
        updated = apply_transition(
            load_task(task_path), load_task_workflow(), trigger, actor, input_data
        )
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"applied {trigger}: {updated.task.state}")


@task.command()
@click.argument("task_path", type=click.Path(path_type=Path))
@click.argument("step_id")
@click.option("--log", "log_summary", help="Required when this completes a Phase.")
@click.option("--evidence", multiple=True, help="Evidence for the completed Phase.")
def done(
    task_path: Path,
    step_id: str,
    log_summary: str | None,
    evidence: tuple[str, ...],
) -> None:
    """Mark the next incomplete Step done."""
    try:
        updated = update_step(
            load_task(task_path),
            load_task_workflow(),
            step_id,
            "done",
            log_summary=log_summary,
            log_evidence=evidence,
        )
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"done {step_id}")


@task.command()
@click.argument("task_path", type=click.Path(path_type=Path))
@click.argument("step_id")
@click.option("--reason", required=True, help="Reason for skipping the Step.")
@click.option("--log", "log_summary", help="Required when this completes a Phase.")
@click.option("--evidence", multiple=True, help="Evidence for the completed Phase.")
def skip(
    task_path: Path,
    step_id: str,
    reason: str,
    log_summary: str | None,
    evidence: tuple[str, ...],
) -> None:
    """Skip the next incomplete Step with a reason."""
    try:
        updated = update_step(
            load_task(task_path),
            load_task_workflow(),
            step_id,
            "skipped",
            reason,
            log_summary,
            evidence,
        )
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"skipped {step_id}")
