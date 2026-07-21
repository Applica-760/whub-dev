"""Task operations shared by whub web adapters."""

from __future__ import annotations

from pathlib import Path

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.project_content import resolve_project_content_root
from whub.wflow.models.task import TaskDocument, TaskSummary
from whub.wflow.services import (
    WflowError,
    list_tasks,
    load_task,
    load_task_workflow,
    render_task_flow,
    resolve_task_reference,
    validate_task,
)


TASKS_RELATIVE_PATH = Path("docs/tasks")


def resolve_project_task_root(manifest: Manifest, project: str) -> Path:
    """Resolve a Project's standard Task directory."""
    task_root = resolve_project_content_root(manifest, project) / TASKS_RELATIVE_PATH
    if task_root.exists() and not task_root.is_dir():
        raise ServiceError(f"project task path is not a directory: {project}")
    return task_root


def list_project_tasks(
    manifest: Manifest,
    project: str,
) -> tuple[TaskSummary, ...]:
    """Return Task summaries from one Project, or an empty result when absent."""
    task_root = resolve_project_task_root(manifest, project)
    if not task_root.exists():
        return ()
    try:
        return list_tasks(task_root)
    except WflowError as error:
        raise ServiceError(str(error)) from error


def load_project_task(
    manifest: Manifest,
    project: str,
    task_id: str,
) -> TaskDocument:
    """Load and validate one Task within one Project."""
    task_root = resolve_project_task_root(manifest, project)
    if not task_root.exists():
        raise NotFoundError(f"task not found: {project}/{task_id}")
    try:
        path = resolve_task_reference(task_id, task_root)
        document = load_task(path)
        diagnostics = validate_task(document, load_task_workflow())
    except WflowError as error:
        if str(error).startswith("task ID not found:"):
            raise NotFoundError(f"task not found: {project}/{task_id}") from error
        raise ServiceError(str(error)) from error
    if diagnostics:
        raise ServiceError(
            "task is invalid: " + "; ".join(item.message for item in diagnostics)
        )
    return document


def render_project_task_flow(
    manifest: Manifest,
    project: str,
    task_id: str,
) -> str:
    """Render one validated Project Task as Mermaid."""
    return render_task_flow(load_project_task(manifest, project, task_id))
