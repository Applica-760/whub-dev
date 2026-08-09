"""Task operations shared by whub web adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whub.services.errors import NotFoundError, ServiceError
from whub.services.manifest import ResolvedManifest
from whub.services.task_resolution import resolve_project_task_storage
from whub.wflow.models.task import TaskDocument, TaskSummary
from whub.wflow.services import (
    WflowError,
    archive_task,
    list_tasks,
    load_task,
    load_task_workflow,
    render_task_flow,
    resolve_task_reference,
    validate_task,
)


def archive_project_task(
    manifest: ResolvedManifest,
    project: str,
    source: Path,
    task: TaskDocument,
) -> Path:
    """Move a terminal Hub Task into the owning Project's frozen archive."""
    destination = resolve_project_task_storage(manifest, project).archive_root
    if task.task.state == "cancelled":
        destination /= "cancelled"
    try:
        return archive_task(source, task, destination)
    except WflowError as error:
        raise ServiceError(str(error)) from error


def list_project_tasks(
    manifest: ResolvedManifest,
    project: str,
) -> tuple[TaskSummary, ...]:
    """Return active and archived Task summaries from one Project."""
    storage = resolve_project_task_storage(manifest, project)
    if not storage.read_roots:
        return ()
    try:
        return list_tasks(*storage.read_roots)
    except WflowError as error:
        raise ServiceError(str(error)) from error


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


def load_project_task(
    manifest: ResolvedManifest,
    project: str,
    task_id: str,
) -> TaskDocument:
    """Load and validate an active or archived Task within one Project."""
    storage = resolve_project_task_storage(manifest, project)
    if not storage.read_roots:
        raise NotFoundError(f"task not found: {project}/{task_id}")
    try:
        path = resolve_task_reference(task_id, *storage.read_roots)
    except WflowError as error:
        if str(error).startswith("task ID not found:"):
            raise NotFoundError(f"task not found: {project}/{task_id}") from error
        raise ServiceError(str(error)) from error
    try:
        document = load_task(path)
        diagnostics = validate_task(document, load_task_workflow())
    except WflowError as error:
        raise ServiceError(str(error)) from error
    if diagnostics:
        raise ServiceError(
            "task is invalid: " + "; ".join(item.message for item in diagnostics)
        )
    return document


def render_project_task_flow(
    manifest: ResolvedManifest,
    project: str,
    task_id: str,
) -> str:
    """Render one validated Project Task as Mermaid."""
    return render_task_flow(load_project_task(manifest, project, task_id))
