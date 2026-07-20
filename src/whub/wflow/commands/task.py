"""Commands for task execution records."""
from __future__ import annotations

from contextlib import chdir
from pathlib import Path

import click

from whub.core.paths import PathError
from whub.models import ManifestError, load_manifest, project_names
from whub.services.errors import ServiceError
from whub.services.project_content import resolve_project_content_root
from whub.utils.render import render_table
from whub.wflow.models.task import TaskDocument
from whub.wflow.services import (
    WflowError,
    append_phase_log,
    archive_task,
    apply_transition,
    complete_step,
    create_task,
    dependency_start_diagnostics,
    delete_plan_item,
    interrupt_task,
    insert_plan_step,
    list_tasks,
    load_task,
    load_task_records,
    load_task_workflow,
    record_acceptance,
    resolve_task_reference,
    resume_task,
    skip_step,
    update_acceptance,
    update_dependency,
    update_plan_item,
    validate_task,
    write_task,
)


@click.group()
@click.option(
    "--project",
    shell_complete=project_names,
    help="Target Project.",
)
@click.pass_context
def task(ctx: click.Context, project: str | None) -> None:
    """Operate task execution records."""
    if project is None:
        return
    try:
        root = resolve_project_content_root(load_manifest(), project)
    except (ManifestError, PathError, ServiceError) as error:
        raise click.ClickException(str(error)) from error
    ctx.with_resource(chdir(root))


@task.command("init")
@click.argument("title")
@click.argument("objective")
@click.option("--approach", "approaches", multiple=True, help="Add one implementation approach.")
def init(title: str, objective: str, approaches: tuple[str, ...]) -> None:
    """Create a draft Task execution record."""
    try:
        path, record = create_task(Path("docs/tasks"), title, objective, approaches)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"initialized {record.task.id}: {path}")


@task.group("plan")
def plan() -> None:
    """Edit a draft Task plan."""


@plan.command("delete")
@click.argument("task_ref")
@click.argument("reference")
def delete(task_ref: str, reference: str) -> None:
    """Logically delete Phase PPP or Step PPP-SSS."""
    try:
        path = resolve_task_reference(task_ref)
        write_task(path, delete_plan_item(load_task(path), reference))
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"deleted {reference}")


@plan.command("insert")
@click.argument("task_ref")
@click.argument("description")
@click.option("--after", help="Insert after Phase PPP or Step PPP-SSS.")
@click.option("--phase-title", help="Create a named Phase with DESCRIPTION as its first Step.")
@click.option("--phase", "phase_ref", help="Add DESCRIPTION to Phase PPP.")
def insert(
    task_ref: str,
    description: str,
    after: str | None,
    phase_title: str | None,
    phase_ref: str | None,
) -> None:
    """Insert a Phase or Step into a draft Task plan."""
    try:
        path = resolve_task_reference(task_ref)
        write_task(
            path,
            insert_plan_step(
                load_task(path),
                description,
                after,
                phase_title,
                phase_ref,
            ),
        )
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"inserted {description}")


@plan.command("update")
@click.argument("task_ref")
@click.argument("reference")
@click.argument("description")
def update(task_ref: str, reference: str, description: str) -> None:
    """Update the title of Phase PPP or description of Step PPP-SSS."""
    try:
        path = resolve_task_reference(task_ref)
        write_task(path, update_plan_item(load_task(path), reference, description))
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"updated {reference}")


@task.group("depends")
def depends() -> None:
    """Edit draft Task dependencies."""


@depends.command("add")
@click.argument("task_ref")
@click.argument("dependency")
def add_dependency(task_ref: str, dependency: str) -> None:
    """Add one dependency TASK-NNN."""
    try:
        path = resolve_task_reference(task_ref)
        write_task(path, update_dependency(load_task(path), dependency, True))
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"added dependency {dependency}")


@depends.command("delete")
@click.argument("task_ref")
@click.argument("dependency")
def delete_dependency(task_ref: str, dependency: str) -> None:
    """Delete one dependency TASK-NNN."""
    try:
        path = resolve_task_reference(task_ref)
        write_task(path, update_dependency(load_task(path), dependency, False))
    except WflowError as error:
        raise click.ClickException(str(error)) from error
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
    try:
        path = resolve_task_reference(task_ref)
        record = load_task(path)
        known_ids = {
            criterion.id
            for phase in record.plan.phases
            for criterion in phase.acceptance
        } | {criterion.id for criterion in record.plan.acceptance} if record.plan else set()
        updated = update_acceptance(record, statement, True, phase_ref)
        added_id = next(
            criterion.id
            for criterion in [
                *updated.plan.acceptance,
                *(criterion for phase in updated.plan.phases for criterion in phase.acceptance),
            ]
            if criterion.id not in known_ids
        )
        write_task(path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"added acceptance {added_id}")


@acceptance.command("delete")
@click.argument("task_ref")
@click.argument("acceptance_ref")
def delete_acceptance(task_ref: str, acceptance_ref: str) -> None:
    """Delete one acceptance criterion ACC-NNN."""
    try:
        path = resolve_task_reference(task_ref)
        write_task(path, update_acceptance(load_task(path), acceptance_ref, False))
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"deleted acceptance {acceptance_ref}")


@task.command()
@click.argument("task_ref")
def check(task_ref: str) -> None:
    """Check one task execution record."""
    try:
        task_path = resolve_task_reference(task_ref)
        task_root = Path("docs/tasks")
        try:
            relative_path = task_path.resolve().relative_to(task_root.resolve()).as_posix()
        except ValueError:
            diagnostics = [
                f"{item.code}: {item.message}"
                for item in validate_task(load_task(task_path), load_task_workflow())
            ]
        else:
            summary = next(
                (
                    item
                    for item in list_tasks(task_root)
                    if item.path == relative_path
                ),
                None,
            )
            if summary is None:
                diagnostics = [
                    f"{item.code}: {item.message}"
                    for item in validate_task(load_task(task_path), load_task_workflow())
                ]
            else:
                diagnostics = summary.diagnostics
    except WflowError as error:
        raise click.ClickException(str(error)) from error

    if not diagnostics:
        click.echo(f"valid {task_path}")
        return
    for diagnostic in diagnostics:
        click.echo(diagnostic, err=True)
    raise click.exceptions.Exit(1)


@task.command("ls")
@click.argument(
    "task_dir",
    required=False,
    default=Path("docs/tasks"),
    type=click.Path(path_type=Path),
)
def ls(task_dir: Path) -> None:
    """List Tasks discovered below TASK_DIR."""
    try:
        tasks = list_tasks(task_dir)
    except WflowError as error:
        raise click.ClickException(str(error)) from error

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
    try:
        task_path = resolve_task_reference(task_ref)
        record = load_task(task_path)
        workflow = load_task_workflow()
        diagnostics = validate_task(record, workflow)
        if diagnostics:
            raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))
        click.echo(f"state: {record.task.state}")
        summary = next(
            (item for item in list_tasks(Path("docs/tasks")) if item.id == record.task.id), None
        )
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
            click.echo(f"Phase {phase_number}: {phase.title}")
            for step_number, step in enumerate(phase.steps, start=1):
                marker = {"done": "x", "skipped": "-"}.get(step.state, " ")
                click.echo(f" [{phase_number:03}-{step_number:03}] [{marker}] {step.description}")
                if step.skip_reason is not None:
                    click.echo(f"    - skipped: {step.skip_reason}")
            for log in phase.log:
                click.echo(f"    - {log}")
    except WflowError as error:
        raise click.ClickException(str(error)) from error


@task.command("transition")
@click.argument("task_ref")
@click.argument("trigger")
@click.option("--actor", required=True, help="Workflow role performing the trigger.")
@click.option("--reason", help="Reason for a plan change or cancellation.")
@click.option("--result", help="Summary recorded when completing a task.")
def transition(task_ref: str, trigger: str, actor: str, reason: str | None, result: str | None) -> None:
    """Apply one declared Workflow trigger."""
    if trigger in {"interrupt_task", "resume_task", "complete_task"}:
        raise click.ClickException(f"trigger '{trigger}' requires the dedicated interruption command")
    input_data = {
        key: value
        for key, value in {"reason": reason, "result": result}.items()
        if value is not None
    }
    try:
        task_path = resolve_task_reference(task_ref)
        record = load_task(task_path)
        if trigger == "approve_plan":
            records = load_task_records(Path("docs/tasks"))
            tasks = {task_id: item for task_id, (_, item) in records.items()}
            tasks[record.task.id] = record
            if diagnostics := dependency_start_diagnostics(record, tasks):
                raise WflowError(
                    "cannot approve plan: "
                    + "; ".join(item.message for item in diagnostics)
                )
        updated = apply_transition(
            record, load_task_workflow(), trigger, actor, input_data
        )
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"transitioned {trigger}: {updated.task.state}")


@task.command("complete")
@click.argument("task_ref")
@click.option("--result", help="Summary recorded when completing an in-progress Task.")
def complete(task_ref: str, result: str | None) -> None:
    """Complete TASK_REF and archive its YAML below docs/tasks/done."""
    try:
        path = resolve_task_reference(task_ref)
        record = load_task(path)
        if record.task.state == "completed":
            updated = record
        else:
            if result is None:
                raise WflowError("--result is required unless task is already completed")
            updated = apply_transition(record, load_task_workflow(), "complete_task", "agent", {"result": result})
        destination = archive_task(path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"completed {updated.task.id}: {destination}")


def _record_for_path(
    path: Path,
    records: dict[str, tuple[Path, TaskDocument]],
) -> tuple[str, TaskDocument]:
    for task_id, (record_path, record) in records.items():
        if record_path.resolve() == path.resolve():
            return task_id, record
    raise WflowError(f"task is not in the task directory: {path}")


@task.command("interrupt")
@click.argument("parent_ref")
@click.argument("child_ref")
@click.option("--reason", required=True, help="Why the parent Task is interrupted.")
@click.option("--task-dir", default=Path("docs/tasks"), type=click.Path(path_type=Path))
def interrupt(parent_ref: str, child_ref: str, reason: str, task_dir: Path) -> None:
    """Freeze PARENT_REF and directly start CHILD_REF as its interruption Task."""
    try:
        records = load_task_records(task_dir)
        parent_path = resolve_task_reference(parent_ref, task_dir)
        child_path = resolve_task_reference(child_ref, task_dir)
        parent_id, parent = _record_for_path(parent_path, records)
        child_id, child = _record_for_path(child_path, records)
        tasks = {task_id: record for task_id, (_, record) in records.items()}
        paused_parent, started_child = interrupt_task(
            parent, child, tasks, load_task_workflow(), reason
        )
        write_task(records[parent_id][0], paused_parent)
        write_task(records[child_id][0], started_child)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"interrupted {parent_id} with {child_id}")


@task.command("resume")
@click.argument("parent_ref")
@click.option("--task-dir", default=Path("docs/tasks"), type=click.Path(path_type=Path))
def resume(parent_ref: str, task_dir: Path) -> None:
    """Resume a paused Task after its interruption Task reaches a terminal state."""
    try:
        records = load_task_records(task_dir)
        parent_path = resolve_task_reference(parent_ref, task_dir)
        parent_id, parent = _record_for_path(parent_path, records)
        tasks = {task_id: record for task_id, (_, record) in records.items()}
        resumed = resume_task(parent, tasks, load_task_workflow())
        write_task(records[parent_id][0], resumed)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"resumed {parent_id}")


@task.command()
@click.argument("task_ref")
@click.argument("acceptance")
@click.option("--status", type=click.Choice(["passed", "failed"]), required=True)
@click.option("--evidence", multiple=True, help="Optional evidence for the acceptance result.")
def accept(
    task_ref: str,
    acceptance: str,
    status: str,
    evidence: tuple[str, ...],
) -> None:
    """Record one acceptance result."""
    try:
        task_path = resolve_task_reference(task_ref)
        updated = record_acceptance(load_task(task_path), acceptance, status, evidence)
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"accepted {acceptance}: {status}")


@task.command("log")
@click.argument("task_ref")
@click.argument("phase_ref")
@click.option("--log", "logs", multiple=True, required=True, help="Line appended to the Phase log.")
def log(task_ref: str, phase_ref: str, logs: tuple[str, ...]) -> None:
    """Append lines to one Phase log without changing Task progress."""
    try:
        task_path = resolve_task_reference(task_ref)
        updated = append_phase_log(load_task(task_path), phase_ref, logs)
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"logged {phase_ref}")


@task.command()
@click.argument("task_ref")
@click.argument("step_ref", required=False)
@click.option("--log", "logs", multiple=True, help="Record a Phase log; required when this completes a Phase.")
def done(
    task_ref: str,
    step_ref: str | None,
    logs: tuple[str, ...],
) -> None:
    """Mark a selected or next incomplete Step done."""
    try:
        task_path = resolve_task_reference(task_ref)
        updated = complete_step(
            load_task(task_path),
            load_task_workflow(),
            step_ref,
            logs,
        )
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"done {step_ref or 'next'}")


@task.command()
@click.argument("task_ref")
@click.argument("step_ref", required=False)
@click.option("--reason", required=True, help="Reason for skipping the Step.")
@click.option("--log", "logs", multiple=True, help="Record a Phase log; required when this completes a Phase.")
def skip(
    task_ref: str,
    step_ref: str | None,
    reason: str,
    logs: tuple[str, ...],
) -> None:
    """Skip a selected or next incomplete Step with a reason."""
    try:
        task_path = resolve_task_reference(task_ref)
        updated = skip_step(
            load_task(task_path),
            load_task_workflow(),
            step_ref,
            reason,
            logs,
        )
        write_task(task_path, updated)
    except WflowError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"skipped {step_ref or 'next'}")
