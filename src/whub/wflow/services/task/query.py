"""Read and derive views from Task execution records."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

from whub.wflow.models.task import TaskDocument, TaskSummary
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task.common import (
    iter_task_paths,
    load_task,
)
from whub.wflow.services.task.integrity import validate_task, validate_task_interruption
from whub.wflow.services.workflow import load_workflow


def load_task_workflow() -> WorkflowDefinition:
    """Load the built-in Workflow definition for task records."""
    resource = files("whub.wflow.definitions").joinpath("task.yaml")
    with as_file(resource) as path:
        return load_workflow(path)


def load_task_records(root: Path) -> dict[str, tuple[Path, TaskDocument]]:
    """Load uniquely identified Task records below ROOT."""
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")

    records: dict[str, tuple[Path, TaskDocument]] = {}
    for path in sorted(iter_task_paths(root)):
        record = load_task(path)
        task_id = record.task.id
        if task_id in records:
            raise WflowError(
                f"duplicate task id: {task_id}: {records[task_id][0]}, {path}"
            )
        records[task_id] = (path, record)
    return records


def list_tasks(root: Path) -> tuple[TaskSummary, ...]:
    """Discover Task YAML files below ROOT and derive their dependency status."""
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")

    workflow = load_task_workflow()
    summaries: list[TaskSummary] = []
    records_by_path: dict[str, TaskDocument] = {}
    for path in sorted(iter_task_paths(root)):
        relative_path = path.relative_to(root).as_posix()
        try:
            record = load_task(path)
        except WflowError as error:
            summaries.append(
                TaskSummary(
                    path=relative_path,
                    diagnostics=[" ".join(str(error).splitlines())],
                )
            )
            continue

        records_by_path[relative_path] = record

        diagnostics = [
            f"{item.code}: {item.message}" for item in validate_task(record, workflow)
        ]
        summaries.append(
            TaskSummary(
                path=relative_path,
                id=record.task.id,
                title=record.task.title,
                state=record.task.state,
                depends_on=record.task.depends_on,
                interruption_task_id=record.task.interruption_task_id,
                interruption_reason=record.task.interruption_reason,
                interruption_source_task_id=record.task.interruption_source_task_id,
                diagnostics=diagnostics,
            )
        )
    ids: dict[str, list[TaskSummary]] = {}
    for summary in summaries:
        if summary.id is not None and not summary.diagnostics:
            ids.setdefault(summary.id, []).append(summary)
    duplicate_ids = {task_id for task_id, items in ids.items() if len(items) > 1}
    records_by_id = {
        task_id: records_by_path[items[0].path]
        for task_id, items in ids.items()
        if len(items) == 1
    }

    updated: list[TaskSummary] = []
    for summary in summaries:
        diagnostics = list(summary.diagnostics)
        if summary.id in duplicate_ids:
            diagnostics.append(f"duplicate task id: {summary.id}")
        elif summary.id is not None and summary.id in records_by_id:
            diagnostics.extend(
                f"{item.code}: {item.message}"
                for item in validate_task_interruption(
                    records_by_id[summary.id], records_by_id
                )
            )
        if diagnostics:
            updated.append(summary.model_copy(update={"diagnostics": diagnostics}))
            continue

        blockers: list[str] = []
        for dependency in summary.depends_on:
            targets = ids.get(dependency, [])
            if not targets:
                blockers.append(f"missing dependency: {dependency}")
            elif dependency in duplicate_ids:
                blockers.append(f"ambiguous dependency: {dependency}")
            elif targets[0].state != "completed":
                blockers.append(
                    f"incomplete dependency: {dependency} ({targets[0].state})"
                )
        updated.append(
            summary.model_copy(
                update={
                    "blocked_by": blockers,
                    "ready": summary.state == "draft" and not blockers,
                    "resumable": (
                        summary.state == "paused"
                        and summary.interruption_task_id in records_by_id
                        and records_by_id[summary.interruption_task_id].task.state
                        in {"completed", "cancelled"}
                    ),
                }
            )
        )
    return tuple(updated)
