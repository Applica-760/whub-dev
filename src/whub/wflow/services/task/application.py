"""Application operations for Task execution records."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import chdir, contextmanager
from dataclasses import replace
from pathlib import Path

from whub.services.manifest import load_manifest
from whub.services.task import archive_project_task
from whub.services.task_resolution import (
    ResolvedProjectTaskStorage,
    resolve_project_task_storage,
)
from whub.wflow.models.task import TaskDocument
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task.common import (
    create_task,
    resolve_task_reference,
    write_task,
)
from whub.wflow.services.task.eligibility import dependency_start_diagnostics
from whub.wflow.services.task.operation import (
    append_phase_log,
    complete_step,
    delete_plan_item,
    insert_plan_step,
    parse_phase_logs,
    record_acceptance,
    restore_plan_item,
    skip_step,
    update_acceptance,
    update_phase_log,
    update_plan_item,
    update_task_header,
)
from whub.wflow.services.task.query import (
    list_tasks,
    load_task,
    load_task_records,
    load_task_workflow,
)
from whub.wflow.services.task.relation import (
    interrupt_task,
    resume_task,
    update_dependency,
)
from whub.wflow.services.task.transition import apply_transition


@contextmanager
def _task_directory(project: str) -> Iterator[ResolvedProjectTaskStorage]:
    storage = resolve_project_task_storage(load_manifest(), project)
    storage.active_root.mkdir(parents=True, exist_ok=True)
    storage = replace(
        storage,
        read_roots=(
            storage.active_root,
            *(root for root in storage.read_roots if root != storage.active_root),
        ),
    )
    with chdir(storage.active_root):
        yield storage


def init_task(
    project: str, title: str, objective: str, approaches: tuple[str, ...]
) -> tuple[Path, TaskDocument]:
    with _task_directory(project) as storage:
        return create_task(
            Path("."),
            title,
            objective,
            approaches,
            id_roots=storage.id_roots,
        )


def update_task(
    project: str,
    task_ref: str,
    title: str | None,
    approaches: tuple[str, ...],
    clear_approaches: bool,
    objective: str | None,
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path,
            update_task_header(
                load_task(path),
                title=title,
                objective=objective,
                approaches=() if clear_approaches else approaches or None,
            ),
        )


def delete_plan(project: str, task_ref: str, reference: str) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(path, delete_plan_item(load_task(path), reference))


def restore_plan(project: str, task_ref: str, reference: str) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(path, restore_plan_item(load_task(path), reference))


def insert_plan(
    project: str,
    task_ref: str,
    description: str,
    after: str | None,
    phase_title: str | None,
    phase_ref: str | None,
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path,
            insert_plan_step(
                load_task(path), description, after, phase_title, phase_ref
            ),
        )


def update_plan(project: str, task_ref: str, reference: str, description: str) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(path, update_plan_item(load_task(path), reference, description))


def update_dependency_for_task(
    project: str, task_ref: str, dependency: str, present: bool
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(path, update_dependency(load_task(path), dependency, present))


def add_acceptance(
    project: str, task_ref: str, statement: str, phase_ref: str | None
) -> str:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        record = load_task(path)
        known_ids = (
            {
                criterion.id
                for phase in record.plan.phases
                for criterion in phase.acceptance
            }
            | {criterion.id for criterion in record.plan.acceptance}
            if record.plan
            else set()
        )
        updated = update_acceptance(record, statement, True, phase_ref)
        added_id = next(
            criterion.id
            for criterion in [
                *updated.plan.acceptance,
                *(
                    criterion
                    for phase in updated.plan.phases
                    for criterion in phase.acceptance
                ),
            ]
            if criterion.id not in known_ids
        )
        write_task(path, updated)
        return added_id


def delete_acceptance(project: str, task_ref: str, acceptance_ref: str) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(path, update_acceptance(load_task(path), acceptance_ref, False))


def check_task(project: str, task_ref: str) -> tuple[Path, tuple[str, ...]]:
    from whub.wflow.services.task.integrity import validate_task

    with _task_directory(project) as storage:
        task_path = resolve_task_reference(task_ref, *storage.read_roots)
        record = load_task(task_path)
        summary = next(
            (
                item
                for item in list_tasks(*storage.read_roots)
                if item.id == record.task.id
            ),
            None,
        )
        diagnostics = (
            summary.diagnostics
            if summary is not None
            else tuple(
                f"{item.code}: {item.message}"
                for item in validate_task(record, load_task_workflow())
            )
        )
        return task_path, tuple(diagnostics)


def list_task_records(project: str, task_dir: Path):
    with _task_directory(project) as storage:
        if task_dir == Path("."):
            return list_tasks(*storage.read_roots)
        return list_tasks(task_dir)


def show_task(project: str, task_ref: str):
    from whub.wflow.services.task.integrity import validate_task

    with _task_directory(project) as storage:
        task_path = resolve_task_reference(task_ref, *storage.read_roots)
        record = load_task(task_path)
        diagnostics = validate_task(record, load_task_workflow())
        if diagnostics:
            raise WflowError(
                "task is invalid: " + "; ".join(item.message for item in diagnostics)
            )
        summary = next(
            (
                item
                for item in list_tasks(*storage.read_roots)
                if item.id == record.task.id
            ),
            None,
        )
        return record, summary


def transition_task(
    project: str,
    task_ref: str,
    trigger: str,
    actor: str,
    input_data: dict[str, str],
) -> tuple[TaskDocument, Path | None]:
    with _task_directory(project) as storage:
        task_path = resolve_task_reference(task_ref)
        record = load_task(task_path)
        if trigger == "approve_plan":
            records = load_task_records(*storage.read_roots)
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
        if updated.task.state == "cancelled":
            return updated, archive_project_task(
                load_manifest(), project, task_path, updated
            )
        write_task(task_path, updated)
        return updated, None


def complete_task(
    project: str, task_ref: str, result: str | None
) -> tuple[TaskDocument, Path]:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        record = load_task(path)
        if record.task.state == "completed":
            updated = record
        else:
            if result is None:
                raise WflowError(
                    "--result is required unless task is already completed"
                )
            updated = apply_transition(
                record,
                load_task_workflow(),
                "complete_task",
                "agent",
                {"result": result},
            )
        return updated, archive_project_task(load_manifest(), project, path, updated)


def _record_for_path(
    path: Path, records: dict[str, tuple[Path, TaskDocument]]
) -> tuple[str, TaskDocument]:
    for task_id, (record_path, record) in records.items():
        if record_path.resolve() == path.resolve():
            return task_id, record
    raise WflowError(f"task is not in the task directory: {path}")


def interrupt(
    project: str, parent_ref: str, child_ref: str, reason: str, task_dir: Path
) -> tuple[str, str]:
    with _task_directory(project) as storage:
        records = (
            load_task_records(*storage.read_roots)
            if task_dir == Path(".")
            else load_task_records(task_dir)
        )
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
        return parent_id, child_id


def resume(project: str, parent_ref: str, task_dir: Path) -> str:
    with _task_directory(project) as storage:
        records = (
            load_task_records(*storage.read_roots)
            if task_dir == Path(".")
            else load_task_records(task_dir)
        )
        parent_path = resolve_task_reference(parent_ref, task_dir)
        parent_id, parent = _record_for_path(parent_path, records)
        tasks = {task_id: record for task_id, (_, record) in records.items()}
        write_task(
            records[parent_id][0], resume_task(parent, tasks, load_task_workflow())
        )
        return parent_id


def accept(
    project: str, task_ref: str, acceptance: str, status: str, evidence: tuple[str, ...]
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path, record_acceptance(load_task(path), acceptance, status, evidence)
        )


def append_log(
    project: str, task_ref: str, phase_ref: str, logs: tuple[str, ...]
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path, append_phase_log(load_task(path), phase_ref, parse_phase_logs(logs))
        )


def update_log(
    project: str, task_ref: str, phase_ref: str, log_ref: str, log: str
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        value = parse_phase_logs((log,))[0]
        write_task(
            path, update_phase_log(load_task(path), phase_ref, log_ref, value=value)
        )


def delete_log(project: str, task_ref: str, phase_ref: str, log_ref: str) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path, update_phase_log(load_task(path), phase_ref, log_ref, deleted=True)
        )


def restore_log(project: str, task_ref: str, phase_ref: str, log_ref: str) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path, update_phase_log(load_task(path), phase_ref, log_ref, deleted=False)
        )


def done(
    project: str, task_ref: str, step_ref: str | None, logs: tuple[str, ...]
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path,
            complete_step(
                load_task(path), load_task_workflow(), step_ref, parse_phase_logs(logs)
            ),
        )


def skip(
    project: str,
    task_ref: str,
    step_ref: str | None,
    reason: str,
    logs: tuple[str, ...],
) -> None:
    with _task_directory(project):
        path = resolve_task_reference(task_ref)
        write_task(
            path,
            skip_step(
                load_task(path),
                load_task_workflow(),
                step_ref,
                reason,
                parse_phase_logs(logs),
            ),
        )
