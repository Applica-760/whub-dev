"""Task read-only JSON API."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from whub.wflow.models.task import TaskDocument, TaskSummary
from whub.wflow.services import (
    WflowError,
    list_tasks,
    load_task,
    load_task_workflow,
    render_task_dependency_graph,
    render_task_flow,
    resolve_task_reference,
    validate_task,
)


TASK_DIR = Path("docs/tasks")

router = APIRouter(prefix="/api/tasks")


class TaskListResponse(BaseModel):
    tasks: list[TaskSummary]


class TaskGraphResponse(BaseModel):
    mermaid: str


@router.get("", response_model=TaskListResponse)
def get_tasks() -> TaskListResponse:
    return TaskListResponse(tasks=list_tasks(TASK_DIR))


@router.get("/graph", response_model=TaskGraphResponse)
def get_task_dependency_graph() -> TaskGraphResponse:
    return TaskGraphResponse(mermaid=render_task_dependency_graph(list_tasks(TASK_DIR)))


@router.get("/{task_id}", response_model=TaskDocument)
def get_task(task_id: str) -> TaskDocument:
    path = resolve_task_reference(task_id, TASK_DIR)
    document = load_task(path)
    diagnostics = validate_task(document, load_task_workflow())
    if diagnostics:
        raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))
    return document


@router.get("/{task_id}/graph", response_model=TaskGraphResponse)
def get_task_flow_graph(task_id: str) -> TaskGraphResponse:
    path = resolve_task_reference(task_id, TASK_DIR)
    document = load_task(path)
    diagnostics = validate_task(document, load_task_workflow())
    if diagnostics:
        raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))
    return TaskGraphResponse(mermaid=render_task_flow(document))
