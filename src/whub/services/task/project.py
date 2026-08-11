"""Project-scoped read models for minimal Task runtime records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from whub.models.flow import TaskRuntime
from whub.services.errors import NotFoundError, ServiceError
from whub.services.flow.errors import FlowError
from whub.services.task.common import load_task_markdown
from whub.services.task.eligibility import dependency_start_diagnostics
from whub.services.task.query import load_task_records
from whub.services.manifest import ResolvedManifest
from whub.services.task_resolution import resolve_project_task_storage


class TaskSummary(BaseModel):
    """Task runtime fields shown in lists and relationship graphs."""

    path: str
    id: str
    title: str | None = None
    state: str
    depends_on: list[str]
    interruption_task_id: str | None = None
    interruption_source_task_id: str | None = None
    blocked_by: list[str]
    ready: bool


class TaskRecord(BaseModel):
    """One Task runtime pair for the detail API."""

    path: str
    title: str | None = None
    markdown: str
    task: TaskRuntime


def _records(
    manifest: ResolvedManifest, project: str
) -> dict[str, tuple[Path, TaskRuntime]]:
    storage = resolve_project_task_storage(manifest, project)
    if not storage.read_roots:
        return {}
    try:
        return load_task_records(*storage.read_roots)
    except FlowError as error:
        raise ServiceError(str(error)) from error


def _title(path: Path) -> str | None:
    for line in load_task_markdown(path).splitlines():
        if line.startswith("# ") and (title := line[2:].strip()):
            return title
    return None


def _summary(
    path: Path, task: TaskRuntime, tasks: dict[str, TaskRuntime]
) -> TaskSummary:
    blocked_by = [
        diagnostic.message for diagnostic in dependency_start_diagnostics(task, tasks)
    ]
    return TaskSummary(
        path=str(path),
        id=task.id,
        title=_title(path),
        state=task.state,
        depends_on=task.depends_on,
        interruption_task_id=task.interruption_task_id,
        interruption_source_task_id=task.interruption_source_task_id,
        blocked_by=blocked_by,
        ready=task.state == "draft" and not blocked_by,
    )


def list_project_tasks(
    manifest: ResolvedManifest, project: str
) -> tuple[TaskSummary, ...]:
    """Return active and archived Task runtime summaries from one Project."""
    records = _records(manifest, project)
    tasks = {task_id: task for task_id, (_, task) in records.items()}
    return tuple(_summary(path, task, tasks) for path, task in records.values())


def list_active_project_tasks(
    manifest: ResolvedManifest, project: str
) -> tuple[TaskSummary, ...]:
    """Return only active Hub Tasks for one Project."""
    storage = resolve_project_task_storage(manifest, project)
    if not storage.active_root.is_dir():
        return ()
    try:
        records = load_task_records(storage.active_root)
    except FlowError as error:
        raise ServiceError(str(error)) from error
    tasks = {task_id: task for task_id, (_, task) in records.items()}
    return tuple(_summary(path, task, tasks) for path, task in records.values())


@dataclass(frozen=True)
class ProjectTasks:
    """One Project's Task summaries, or the error that prevented reading them."""

    project: str
    tasks: tuple[TaskSummary, ...] = ()
    error: str | None = None


def list_all_project_tasks(manifest: ResolvedManifest) -> tuple[ProjectTasks, ...]:
    """Return every Project's Task summaries, isolating per-Project failures."""
    results: list[ProjectTasks] = []
    for project in manifest.projects:
        try:
            tasks = list_project_tasks(manifest, project.name)
        except (ServiceError, OSError) as error:
            results.append(ProjectTasks(project=project.name, error=str(error)))
            continue
        results.append(ProjectTasks(project=project.name, tasks=tasks))
    return tuple(results)


def list_all_active_project_tasks(
    manifest: ResolvedManifest,
) -> tuple[ProjectTasks, ...]:
    """Return active Hub Task summaries without reading Project histories."""
    results: list[ProjectTasks] = []
    for project in manifest.projects:
        try:
            tasks = list_active_project_tasks(manifest, project.name)
        except (ServiceError, OSError) as error:
            results.append(ProjectTasks(project=project.name, error=str(error)))
            continue
        results.append(ProjectTasks(project=project.name, tasks=tasks))
    return tuple(results)


def load_project_task(
    manifest: ResolvedManifest,
    project: str,
    task_id: str,
) -> TaskRecord:
    """Load one active or archived Task runtime pair within PROJECT."""
    records = _records(manifest, project)
    resolved_id = task_id if task_id.startswith("TASK-") else f"TASK-{task_id}"
    try:
        path, task = records[resolved_id]
    except KeyError as error:
        raise NotFoundError(f"task not found: {project}/{task_id}") from error
    return TaskRecord(
        path=str(path),
        title=_title(path),
        markdown=load_task_markdown(path),
        task=task,
    )


def load_active_project_task(
    manifest: ResolvedManifest, project: str, task_id: str
) -> TaskRecord:
    """Load one active Hub Task without accessing Project history."""
    storage = resolve_project_task_storage(manifest, project)
    if not storage.active_root.is_dir():
        raise NotFoundError(f"task not found: {project}/{task_id}")
    try:
        records = load_task_records(storage.active_root)
    except FlowError as error:
        raise ServiceError(str(error)) from error
    resolved_id = task_id if task_id.startswith("TASK-") else f"TASK-{task_id}"
    try:
        path, task = records[resolved_id]
    except KeyError as error:
        raise NotFoundError(f"task not found: {project}/{task_id}") from error
    return TaskRecord(
        path=str(path), title=_title(path), markdown=load_task_markdown(path), task=task
    )
