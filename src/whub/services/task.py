"""Task operations shared by whub web adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from whub.core.context import current_context
from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.project_content import resolve_project_content_root
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


TASKS_RELATIVE_PATH = Path("wflow/tasks")


def resolve_project_task_root(manifest: Manifest, project: str) -> Path:
    """Resolve PROJECT's Hub-owned active Task directory."""
    if manifest.resolve_project(project) is None:
        raise ServiceError(f"unknown project: {project}")
    task_root = current_context().workspace_root / TASKS_RELATIVE_PATH / project
    if task_root.exists() and not task_root.is_dir():
        raise ServiceError(f"Hub task path is not a directory: {project}")
    return task_root


def resolve_project_task_history_root(manifest: Manifest, project: str) -> Path | None:
    """Resolve PROJECT's Task history directory for ID allocation."""
    root = resolve_project_content_root(manifest, project) / "docs/tasks"
    return root if root.exists() else None


def resolve_project_task_archive_root(manifest: Manifest, project: str) -> Path | None:
    """Resolve PROJECT's terminal Task archive directory."""
    root = resolve_project_content_root(manifest, project) / "docs/tasks/done"
    return root if root.exists() else None


def project_task_root(manifest: Manifest, project: str) -> Path | None:
    """Return PROJECT's active Hub Task directory, when it exists."""
    task_root = resolve_project_task_root(manifest, project)
    return task_root if task_root.exists() else None


def archive_project_task(
    manifest: Manifest,
    project: str,
    source: Path,
    task: TaskDocument,
) -> Path:
    """Move a terminal Hub Task into the owning Project's frozen archive."""
    destination = resolve_project_content_root(manifest, project) / "docs/tasks/done"
    if task.task.state == "cancelled":
        destination /= "cancelled"
    try:
        return archive_task(source, task, destination)
    except WflowError as error:
        raise ServiceError(str(error)) from error


def list_project_tasks(
    manifest: Manifest,
    project: str,
) -> tuple[TaskSummary, ...]:
    """Return active and archived Task summaries from one Project."""
    task_root = project_task_root(manifest, project)
    archive_root = resolve_project_task_archive_root(manifest, project)
    try:
        active_tasks = list_tasks(task_root) if task_root is not None else ()
        archived_tasks = list_tasks(archive_root) if archive_root is not None else ()
        return (*active_tasks, *archived_tasks)
    except WflowError as error:
        raise ServiceError(str(error)) from error


@dataclass(frozen=True)
class ProjectTasks:
    """One Project's Task summaries, or the error that prevented reading them."""

    project: str
    tasks: tuple[TaskSummary, ...] = ()
    error: str | None = None


def list_all_project_tasks(manifest: Manifest) -> tuple[ProjectTasks, ...]:
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
    manifest: Manifest,
    project: str,
    task_id: str,
) -> TaskDocument:
    """Load and validate an active or archived Task within one Project."""
    roots = (
        root
        for root in (
            project_task_root(manifest, project),
            resolve_project_task_archive_root(manifest, project),
        )
        if root is not None
    )
    for root in roots:
        try:
            path = resolve_task_reference(task_id, root)
        except WflowError as error:
            if str(error).startswith("task ID not found:"):
                continue
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
    raise NotFoundError(f"task not found: {project}/{task_id}")


def render_project_task_flow(
    manifest: Manifest,
    project: str,
    task_id: str,
) -> str:
    """Render one validated Project Task as Mermaid."""
    return render_task_flow(load_project_task(manifest, project, task_id))
