"""Read and derive views from Task execution records."""
from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path
import re

import yaml
from pydantic import ValidationError

from whub.wflow.models.task import TASK_ID_PATTERN, TaskDocument, TaskSummary
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task_validation import validate_task, validate_task_interruption
from whub.wflow.services.workflow import load_workflow


def load_task(path: Path) -> TaskDocument:
    """Load one task execution record from YAML."""
    try:
        return TaskDocument.model_validate(yaml.safe_load(path.read_text()))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise WflowError(f"failed to load task YAML: {path}: {error}") from error


def resolve_task_reference(
    reference: str,
    root: Path = Path("docs/tasks"),
) -> Path:
    """Resolve a Task ID or its numeric part in ROOT, or a YAML path."""
    task_id = (
        reference
        if re.fullmatch(TASK_ID_PATTERN, reference) is not None
        else f"TASK-{reference}" if re.fullmatch(r"[0-9]+", reference) else None
    )
    if task_id is None:
        return Path(reference)
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")

    matches: list[Path] = []
    for path in sorted(root.rglob("*.yaml")):
        try:
            if load_task(path).task.id == task_id:
                matches.append(path)
        except WflowError:
            continue
    if not matches:
        raise WflowError(f"task ID not found: {task_id}")
    if len(matches) > 1:
        paths = ", ".join(str(path) for path in matches)
        raise WflowError(f"task ID is ambiguous: {task_id}: {paths}")
    return matches[0]


def load_task_workflow() -> WorkflowDefinition:
    """Load the built-in Workflow definition for task records."""
    resource = files("whub.wflow.definitions").joinpath("task.yaml")
    with as_file(resource) as path:
        return load_workflow(path)


def list_tasks(root: Path) -> tuple[TaskSummary, ...]:
    """Discover Task YAML files below ROOT and derive their dependency status."""
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")

    workflow = load_task_workflow()
    summaries: list[TaskSummary] = []
    records_by_path: dict[str, TaskDocument] = {}
    for path in sorted(root.rglob("*.yaml")):
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
                for item in validate_task_interruption(records_by_id[summary.id], records_by_id)
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
                }
            )
        )
    return tuple(updated)
