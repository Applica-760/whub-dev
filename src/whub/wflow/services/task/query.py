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


def load_task_records(
    root: Path = Path("."), *additional_roots: Path
) -> dict[str, tuple[Path, TaskDocument]]:
    """Load uniquely identified Task records below ordered roots."""
    roots = (root, *additional_roots)
    for task_root in roots:
        if not task_root.is_dir():
            raise WflowError(f"task directory does not exist: {task_root}")

    records: dict[str, tuple[Path, TaskDocument]] = {}
    for task_root in roots:
        for path in sorted(iter_task_paths(task_root)):
            record = load_task(path)
            task_id = record.task.id
            if task_id in records:
                raise WflowError(
                    f"duplicate task id: {task_id}: {records[task_id][0]}, {path}"
                )
            records[task_id] = (path, record)
    return records


def list_tasks(
    root: Path = Path("."), *additional_roots: Path
) -> tuple[TaskSummary, ...]:
    """Discover Tasks below ordered roots and derive shared relation status."""
    roots = (root, *additional_roots)
    for task_root in roots:
        if not task_root.is_dir():
            raise WflowError(f"task directory does not exist: {task_root}")

    workflow = load_task_workflow()
    entries: list[tuple[TaskSummary, TaskDocument | None]] = []
    for task_root in roots:
        for path in sorted(iter_task_paths(task_root)):
            relative_path = path.relative_to(task_root).as_posix()
            try:
                record = load_task(path)
            except WflowError as error:
                entries.append(
                    (
                        TaskSummary(
                            path=relative_path,
                            diagnostics=[" ".join(str(error).splitlines())],
                        ),
                        None,
                    )
                )
                continue

            diagnostics = [
                f"{item.code}: {item.message}"
                for item in validate_task(record, workflow)
            ]
            entries.append(
                (
                    TaskSummary(
                        path=relative_path,
                        id=record.task.id,
                        title=record.task.title,
                        state=record.task.state,
                        depends_on=record.task.depends_on,
                        interruption_task_id=record.task.interruption_task_id,
                        interruption_reason=record.task.interruption_reason,
                        interruption_source_task_id=(
                            record.task.interruption_source_task_id
                        ),
                        diagnostics=diagnostics,
                    ),
                    record,
                )
            )

    ids: dict[str, list[int]] = {}
    for index, (summary, _) in enumerate(entries):
        if summary.id is not None and not summary.diagnostics:
            ids.setdefault(summary.id, []).append(index)
    duplicate_ids = {task_id for task_id, indexes in ids.items() if len(indexes) > 1}
    records_by_id: dict[str, TaskDocument] = {}
    for task_id, indexes in ids.items():
        if len(indexes) != 1:
            continue
        record = entries[indexes[0]][1]
        assert record is not None
        records_by_id[task_id] = record

    updated: list[TaskSummary] = []
    for summary, _ in entries:
        diagnostics = list(summary.diagnostics)
        if summary.id in duplicate_ids:
            diagnostics.append(f"duplicate task id: {summary.id}")
        elif summary.id is not None and summary.id in records_by_id:
            record = records_by_id[summary.id]
            diagnostics.extend(
                f"{item.code}: {item.message}"
                for item in validate_task_interruption(record, records_by_id)
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
            else:
                dependency_summary = entries[targets[0]][0]
                if dependency_summary.state == "completed":
                    continue
                blockers.append(
                    f"incomplete dependency: {dependency} ({dependency_summary.state})"
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
