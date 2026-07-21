"""Task read-only JSON API."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.models import load_manifest
from whub.services.task import (
    list_project_tasks,
    load_project_task,
    render_project_task_flow,
)
from whub.wflow.models.task import TaskDocument, TaskSummary

router = APIRouter(prefix="/api/tasks")


class TaskListResponse(BaseModel):
    tasks: list[TaskSummary]


class TaskGraphResponse(BaseModel):
    mermaid: str


@router.get("", response_model=TaskListResponse)
def get_tasks(project: str = "workspace-hub") -> TaskListResponse:
    return TaskListResponse(tasks=list_project_tasks(load_manifest(), project))


@router.get("/{task_id}", response_model=TaskDocument)
def get_task(task_id: str, project: str = "workspace-hub") -> TaskDocument:
    return load_project_task(load_manifest(), project, task_id)


@router.get("/{task_id}/graph", response_model=TaskGraphResponse)
def get_task_flow_graph(
    task_id: str,
    project: str = "workspace-hub",
) -> TaskGraphResponse:
    return TaskGraphResponse(
        mermaid=render_project_task_flow(load_manifest(), project, task_id),
    )
