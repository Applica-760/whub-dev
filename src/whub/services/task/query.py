"""Read and validate Task runtime records across storage roots."""

from __future__ import annotations

from pathlib import Path

from whub.models.flow import TaskRuntime
from whub.services.flow.definitions import task_workflow
from whub.services.flow.errors import FlowError
from whub.services.task.common import (
    iter_task_paths,
    load_task,
    load_task_markdown,
)
from whub.services.task.integrity import validate_task_set


def load_task_records(
    root: Path = Path("."), *additional_roots: Path
) -> dict[str, tuple[Path, TaskRuntime]]:
    """Load one complete YAML/Markdown pair for each unique Task ID."""
    roots = (root, *additional_roots)
    for task_root in roots:
        if not task_root.is_dir():
            raise FlowError(f"task directory does not exist: {task_root}")

    records: dict[str, tuple[Path, TaskRuntime]] = {}
    for task_root in roots:
        for path in sorted(iter_task_paths(task_root)):
            task = load_task(path)
            load_task_markdown(path)
            if previous := records.get(task.id):
                raise FlowError(f"duplicate task id: {task.id}: {previous[0]}, {path}")
            records[task.id] = (path, task)

    if diagnostics := validate_task_set(
        {task_id: task for task_id, (_, task) in records.items()}, task_workflow()
    ):
        details = "; ".join(
            f"{task_id}: {item.code}: {item.message}" for task_id, item in diagnostics
        )
        raise FlowError(f"task set is invalid: {details}")
    return records
