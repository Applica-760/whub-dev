"""Persisted Task runtime operations."""

from __future__ import annotations

import json
from pathlib import Path

from whub.models.flow import TaskRuntime
from whub.services.flow.definitions import task_workflow
from whub.services.flow.errors import FlowError
from whub.services.task.common import archive_task, write_task_set
from whub.services.task.eligibility import dependency_start_diagnostics
from whub.services.task.log import append_task_log
from whub.services.task.query import load_task_records
from whub.services.task.relation import (
    interrupt_task,
    resume_task,
    update_dependency,
)
from whub.services.task.transition import apply_transition


def update_dependency_for_task(
    active_root: Path,
    task_ref: str,
    dependency: str,
    present: bool,
    *additional_roots: Path,
) -> TaskRuntime:
    records = load_task_records(active_root, *additional_roots)
    path, task = _active_record(records, active_root, task_ref)
    updated = update_dependency(task, dependency, present)
    write_task_set({path: updated})
    return updated


def start_task(
    active_root: Path, task_ref: str, *additional_roots: Path
) -> TaskRuntime:
    records = load_task_records(active_root, *additional_roots)
    path, task = _active_record(records, active_root, task_ref)
    if diagnostics := dependency_start_diagnostics(task, _tasks(records)):
        raise FlowError(
            "cannot start task: " + "; ".join(item.message for item in diagnostics)
        )
    updated = apply_transition(task, task_workflow(), "start_task")
    write_task_set({path: updated})
    return updated


def interrupt(
    active_root: Path,
    parent_ref: str,
    child_ref: str,
    reason: str,
    *additional_roots: Path,
) -> tuple[TaskRuntime, TaskRuntime]:
    records = load_task_records(active_root, *additional_roots)
    parent_path, parent = _active_record(records, active_root, parent_ref)
    child_path, child = _active_record(records, active_root, child_ref)
    paused_parent, started_child = interrupt_task(
        parent, child, _tasks(records), task_workflow(), reason
    )
    write_task_set({parent_path: paused_parent, child_path: started_child})
    append_task_log(
        parent_path,
        json.dumps({"fact": f"interrupted by {started_child.id}: {reason}"}),
        "user",
    )
    return paused_parent, started_child


def resume(active_root: Path, parent_ref: str, *additional_roots: Path) -> TaskRuntime:
    records = load_task_records(active_root, *additional_roots)
    path, parent = _active_record(records, active_root, parent_ref)
    updated = resume_task(parent, _tasks(records), task_workflow())
    write_task_set({path: updated})
    return updated


def complete_task(
    active_root: Path,
    archive_root: Path,
    task_ref: str,
    *additional_roots: Path,
) -> Path:
    records = load_task_records(active_root, *additional_roots)
    path, task = _active_record(records, active_root, task_ref)
    updated = (
        task
        if task.state == "completed"
        else apply_transition(task, task_workflow(), "complete_task")
    )
    return archive_task(path, updated, archive_root)


def cancel_task(
    active_root: Path,
    archive_root: Path,
    task_ref: str,
    reason: str,
    *additional_roots: Path,
) -> Path:
    if not reason.strip():
        raise FlowError("cancellation reason is required")
    records = load_task_records(active_root, *additional_roots)
    path, task = _active_record(records, active_root, task_ref)
    updated = apply_transition(
        task, task_workflow(), "cancel_task", {"reason": reason.strip()}
    )
    append_task_log(path, json.dumps({"fact": f"cancelled: {reason.strip()}"}), "user")
    return archive_task(path, updated, archive_root)


def _active_record(
    records: dict[str, tuple[Path, TaskRuntime]], active_root: Path, task_ref: str
) -> tuple[Path, TaskRuntime]:
    task_id = f"TASK-{task_ref.removeprefix('TASK-')}"
    if task_id not in records:
        raise FlowError(f"task ID not found: {task_ref}")
    path, task = records[task_id]
    if not path.is_relative_to(active_root):
        raise FlowError(f"task is archived: {task_id}")
    return path, task


def _tasks(records: dict[str, tuple[Path, TaskRuntime]]) -> dict[str, TaskRuntime]:
    return {task_id: task for task_id, (_, task) in records.items()}
