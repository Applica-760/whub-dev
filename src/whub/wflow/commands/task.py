"""Click commands for Task execution records."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from whub.commands import project_names
from whub.models import ManifestError
from whub.services.errors import ServiceError
from whub.utils.render import render_table
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task import application


_PHASE_LOG_HELP = (
    "JSON object with one non-empty string key-value pair. "
    'Example: --log \'{"finding":"確認結果"}\''
)


def _invoke(operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return operation(*args, **kwargs)
    except (ManifestError, OSError, ServiceError, WflowError) as error:
        raise click.ClickException(str(error)) from error


def _project() -> str:
    return click.get_current_context().meta["task_project"]


@click.group()
@click.option(
    "--project",
    default="whub-dev",
    show_default=True,
    shell_complete=project_names,
    help="Target Project.",
)
@click.pass_context
def task(ctx: click.Context, project: str) -> None:
    """Operate task execution records."""
    ctx.meta["task_project"] = project


@task.command("init")
@click.argument("title")
@click.argument("objective")
@click.option(
    "--approach", "approaches", multiple=True, help="Add one implementation approach."
)
def init(title: str, objective: str, approaches: tuple[str, ...]) -> None:
    """Create a draft Task execution record."""
    path, record = _invoke(
        application.init_task, _project(), title, objective, approaches
    )
    click.echo(f"initialized {record.task.id}: {path}")


@task.command("update")
@click.argument("task_ref")
@click.option("--title", help="Replace the Task title.")
@click.option("--objective", help="Replace the Task objective.")
@click.option(
    "--approach",
    "approaches",
    multiple=True,
    help="Replace approaches; repeat for each approach.",
)
@click.option("--clear-approaches", is_flag=True, help="Remove all approaches.")
def update_task(
    task_ref: str,
    title: str | None,
    objective: str | None,
    approaches: tuple[str, ...],
    clear_approaches: bool,
) -> None:
    """Update Task title, objective, or approaches."""
    if clear_approaches and approaches:
        raise click.UsageError("--clear-approaches cannot be used with --approach")
    _invoke(
        application.update_task,
        _project(),
        task_ref,
        title,
        approaches,
        clear_approaches,
        objective,
    )
    click.echo(f"updated {task_ref}")


@task.group("plan")
def plan() -> None:
    """Edit a draft or in-progress Task plan."""


@plan.command("delete")
@click.argument("task_ref")
@click.argument("reference")
def delete(task_ref: str, reference: str) -> None:
    """Logically delete Phase PPP or Step PPP-SSS."""
    _invoke(application.delete_plan, _project(), task_ref, reference)
    click.echo(f"deleted {reference}")


@plan.command("restore")
@click.argument("task_ref")
@click.argument("reference")
def restore(task_ref: str, reference: str) -> None:
    """Restore logically deleted Phase or Step."""
    _invoke(application.restore_plan, _project(), task_ref, reference)
    click.echo(f"restored {reference}")


@plan.command("insert")
@click.argument("task_ref")
@click.argument("description")
@click.option("--after", help="Insert after Phase PPP or Step PPP-SSS.")
@click.option(
    "--phase-title", help="Create a named Phase with DESCRIPTION as its first Step."
)
@click.option("--phase", "phase_ref", help="Add DESCRIPTION to Phase PPP.")
def insert(
    task_ref: str,
    description: str,
    after: str | None,
    phase_title: str | None,
    phase_ref: str | None,
) -> None:
    """Insert a Phase or Step into a draft or in-progress Task plan."""
    _invoke(
        application.insert_plan,
        _project(),
        task_ref,
        description,
        after,
        phase_title,
        phase_ref,
    )
    click.echo(f"inserted {description}")


@plan.command("update")
@click.argument("task_ref")
@click.argument("reference")
@click.argument("description")
def update(task_ref: str, reference: str, description: str) -> None:
    """Update the title of Phase PPP or description of Step PPP-SSS."""
    _invoke(application.update_plan, _project(), task_ref, reference, description)
    click.echo(f"updated {reference}")


@task.group("depends")
def depends() -> None:
    """Edit draft Task dependencies."""


@depends.command("add")
@click.argument("task_ref")
@click.argument("dependency")
def add_dependency(task_ref: str, dependency: str) -> None:
    """Add one dependency TASK-NNN."""
    _invoke(
        application.update_dependency_for_task, _project(), task_ref, dependency, True
    )
    click.echo(f"added dependency {dependency}")


@depends.command("delete")
@click.argument("task_ref")
@click.argument("dependency")
def delete_dependency(task_ref: str, dependency: str) -> None:
    """Delete one dependency TASK-NNN."""
    _invoke(
        application.update_dependency_for_task, _project(), task_ref, dependency, False
    )
    click.echo(f"deleted dependency {dependency}")


@task.group("acceptance")
def acceptance() -> None:
    """Edit draft Task acceptance criteria."""


@acceptance.command("add")
@click.argument("task_ref")
@click.argument("statement")
@click.option("--phase", "phase_ref", help="Add the criterion to Phase PPP.")
def add_acceptance(task_ref: str, statement: str, phase_ref: str | None) -> None:
    """Add one acceptance criterion."""
    added_id = _invoke(
        application.add_acceptance, _project(), task_ref, statement, phase_ref
    )
    click.echo(f"added acceptance {added_id}")


@acceptance.command("delete")
@click.argument("task_ref")
@click.argument("acceptance_ref")
def delete_acceptance(task_ref: str, acceptance_ref: str) -> None:
    """Delete one acceptance criterion ACC-NNN."""
    _invoke(application.delete_acceptance, _project(), task_ref, acceptance_ref)
    click.echo(f"deleted acceptance {acceptance_ref}")


@task.command()
@click.argument("task_ref")
def check(task_ref: str) -> None:
    """Check one task execution record."""
    task_path, diagnostics = _invoke(application.check_task, _project(), task_ref)
    if not diagnostics:
        click.echo(f"valid {task_path}")
        return
    for diagnostic in diagnostics:
        click.echo(diagnostic, err=True)
    raise click.exceptions.Exit(1)


@task.command("ls")
@click.argument(
    "task_dir", required=False, default=Path("."), type=click.Path(path_type=Path)
)
def ls(task_dir: Path) -> None:
    """List Tasks discovered below TASK_DIR."""
    tasks = _invoke(application.list_task_records, _project(), task_dir)
    render_table(
        [
            (
                item.path,
                item.id or "-",
                item.state or "invalid",
                ",".join(item.depends_on) or "-",
                item.interruption_source_task_id or "-",
                item.interruption_task_id or "-",
                "yes" if item.resumable else "no",
                "; ".join(item.blocked_by) or "-",
                "yes" if item.ready else "no",
                "; ".join(item.diagnostics) or "-",
            )
            for item in tasks
        ],
        headers=(
            "path",
            "id",
            "state",
            "depends_on",
            "interruption_source",
            "interruption_task",
            "resumable",
            "blocked_by",
            "ready",
            "diagnostics",
        ),
    )


@task.command()
@click.argument("task_ref")
def show(task_ref: str) -> None:
    """Show task state and plan progress."""
    record, summary = _invoke(application.show_task, _project(), task_ref)
    click.echo(f"state: {record.task.state}")
    if summary is not None:
        if summary.interruption_source_task_id is not None:
            click.echo(f"interruption source: {summary.interruption_source_task_id}")
        if summary.interruption_task_id is not None:
            click.echo(f"interruption task: {summary.interruption_task_id}")
            click.echo(f"interruption reason: {summary.interruption_reason}")
        if record.task.state == "paused":
            click.echo(f"resumable: {'yes' if summary.resumable else 'no'}")
    if record.plan is None:
        click.echo("plan: -")
        return
    for phase_number, phase in enumerate(record.plan.phases, start=1):
        click.echo()
        phase_title = f"~~{phase.title}~~" if phase.deleted else phase.title
        click.echo(f"Phase {phase_number}: {phase_title}")
        for step_number, step in enumerate(phase.steps, start=1):
            marker = {"done": "x", "skipped": "-"}.get(step.state, " ")
            description = (
                f"~~{step.description}~~"
                if phase.deleted or step.deleted
                else step.description
            )
            click.echo(
                f" [{phase_number:03}-{step_number:03}] [{marker}] {description}"
            )
            if step.skip_reason is not None:
                click.echo(f"    - skipped: {step.skip_reason}")
        for log in phase.log:
            if isinstance(log, str):
                click.echo(f"    - {log}")
                continue
            key, value = next(iter(log.value.items()))
            text = f"[{key}]: {value}"
            click.echo(f"    - {'~~' + text + '~~' if log.deleted else text}")


@task.command("transition")
@click.argument("task_ref")
@click.argument("trigger")
@click.option("--actor", required=True, help="Workflow role performing the trigger.")
@click.option("--reason", help="Reason for a plan change or cancellation.")
@click.option("--result", help="Summary recorded when completing a task.")
def transition(
    task_ref: str, trigger: str, actor: str, reason: str | None, result: str | None
) -> None:
    """Apply one declared Workflow trigger."""
    if trigger in {"interrupt_task", "resume_task", "complete_task"}:
        raise click.ClickException(
            f"trigger '{trigger}' requires the dedicated interruption command"
        )
    input_data = {
        key: value
        for key, value in {"reason": reason, "result": result}.items()
        if value is not None
    }
    updated, destination = _invoke(
        application.transition_task, _project(), task_ref, trigger, actor, input_data
    )
    if destination is not None:
        click.echo(f"cancelled {updated.task.id}: {destination}")
        return
    click.echo(f"transitioned {trigger}: {updated.task.state}")


@task.command("complete")
@click.argument("task_ref")
@click.option("--result", help="Summary recorded when completing an in-progress Task.")
def complete(task_ref: str, result: str | None) -> None:
    """Complete TASK_REF and archive its YAML below done."""
    updated, destination = _invoke(
        application.complete_task, _project(), task_ref, result
    )
    click.echo(f"completed {updated.task.id}: {destination}")


@task.command("interrupt")
@click.argument("parent_ref")
@click.argument("child_ref")
@click.option("--reason", required=True, help="Why the parent Task is interrupted.")
@click.option("--task-dir", default=Path("."), type=click.Path(path_type=Path))
def interrupt(parent_ref: str, child_ref: str, reason: str, task_dir: Path) -> None:
    """Freeze PARENT_REF and directly start CHILD_REF as its interruption Task."""
    parent_id, child_id = _invoke(
        application.interrupt, _project(), parent_ref, child_ref, reason, task_dir
    )
    click.echo(f"interrupted {parent_id} with {child_id}")


@task.command("resume")
@click.argument("parent_ref")
@click.option("--task-dir", default=Path("."), type=click.Path(path_type=Path))
def resume(parent_ref: str, task_dir: Path) -> None:
    """Resume a paused Task after its interruption Task reaches a terminal state."""
    parent_id = _invoke(application.resume, _project(), parent_ref, task_dir)
    click.echo(f"resumed {parent_id}")


@task.command()
@click.argument("task_ref")
@click.argument("acceptance")
@click.option("--status", type=click.Choice(["passed", "failed"]), required=True)
@click.option(
    "--evidence", multiple=True, help="Optional evidence for the acceptance result."
)
def accept(
    task_ref: str, acceptance: str, status: str, evidence: tuple[str, ...]
) -> None:
    """Record one acceptance result."""
    _invoke(application.accept, _project(), task_ref, acceptance, status, evidence)
    click.echo(f"accepted {acceptance}: {status}")


@task.command("log")
@click.argument("task_ref")
@click.argument("phase_ref")
@click.option(
    "--log",
    "logs",
    multiple=True,
    required=True,
    help=f"{_PHASE_LOG_HELP} Appends to the Phase log.",
)
def log(task_ref: str, phase_ref: str, logs: tuple[str, ...]) -> None:
    """Append lines to one Phase log without changing Task progress."""
    _invoke(application.append_log, _project(), task_ref, phase_ref, logs)
    click.echo(f"logged {phase_ref}")


@task.command("log-update")
@click.argument("task_ref")
@click.argument("phase_ref")
@click.argument("log_ref")
@click.option(
    "--log",
    "log",
    required=True,
    help=f"{_PHASE_LOG_HELP} Replaces the selected Phase log entry.",
)
def log_update(task_ref: str, phase_ref: str, log_ref: str, log: str) -> None:
    """Replace one active structured Phase Log entry."""
    _invoke(application.update_log, _project(), task_ref, phase_ref, log_ref, log)
    click.echo(f"updated log {phase_ref}-{log_ref}")


@task.command("log-delete")
@click.argument("task_ref")
@click.argument("phase_ref")
@click.argument("log_ref")
def log_delete(task_ref: str, phase_ref: str, log_ref: str) -> None:
    """Logically delete one structured Phase Log entry."""
    _invoke(application.delete_log, _project(), task_ref, phase_ref, log_ref)
    click.echo(f"deleted log {phase_ref}-{log_ref}")


@task.command("log-restore")
@click.argument("task_ref")
@click.argument("phase_ref")
@click.argument("log_ref")
def log_restore(task_ref: str, phase_ref: str, log_ref: str) -> None:
    """Restore one logically deleted structured Phase Log entry."""
    _invoke(application.restore_log, _project(), task_ref, phase_ref, log_ref)
    click.echo(f"restored log {phase_ref}-{log_ref}")


@task.command()
@click.argument("task_ref")
@click.argument("step_ref", required=False)
@click.option(
    "--log",
    "logs",
    multiple=True,
    help=f"{_PHASE_LOG_HELP} Required when this completes a Phase.",
)
def done(task_ref: str, step_ref: str | None, logs: tuple[str, ...]) -> None:
    """Mark a selected or next incomplete Step done."""
    _invoke(application.done, _project(), task_ref, step_ref, logs)
    click.echo(f"done {step_ref or 'next'}")


@task.command()
@click.argument("task_ref")
@click.argument("step_ref", required=False)
@click.option("--reason", required=True, help="Reason for skipping the Step.")
@click.option(
    "--log",
    "logs",
    multiple=True,
    help=f"{_PHASE_LOG_HELP} Required when this completes a Phase.",
)
def skip(
    task_ref: str, step_ref: str | None, reason: str, logs: tuple[str, ...]
) -> None:
    """Skip a selected or next incomplete Step with a reason."""
    _invoke(application.skip, _project(), task_ref, step_ref, reason, logs)
    click.echo(f"skipped {step_ref or 'next'}")
