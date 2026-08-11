"""Task read-only JSON API."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.services.manifest import load_manifest
from whub.services.task.project import (
    list_all_active_project_tasks,
    list_all_project_tasks,
    list_active_project_tasks,
    list_project_tasks,
    load_active_project_task,
    load_project_task,
    TaskRecord,
    TaskSummary,
)

router = APIRouter(prefix="/api/tasks")


class TaskListResponse(BaseModel):
    tasks: list[TaskSummary]


class ProjectTasksResponse(BaseModel):
    project: str
    tasks: list[TaskSummary]
    error: str | None = None


class AllTasksResponse(BaseModel):
    projects: list[ProjectTasksResponse]


@router.get("", response_model=TaskListResponse)
def get_tasks(project: str = "whub-dev") -> TaskListResponse:
    return TaskListResponse(tasks=list_project_tasks(load_manifest(), project))


@router.get("/active", response_model=TaskListResponse)
def get_active_tasks(project: str = "whub-dev") -> TaskListResponse:
    return TaskListResponse(tasks=list_active_project_tasks(load_manifest(), project))


# "/all"は"/{task_id}"より前に宣言してPathパラメータへ吸われないようにする
@router.get("/all", response_model=AllTasksResponse)
def get_all_tasks() -> AllTasksResponse:
    return AllTasksResponse(
        projects=[
            ProjectTasksResponse(
                project=item.project,
                tasks=list(item.tasks),
                error=item.error,
            )
            for item in list_all_project_tasks(load_manifest())
        ],
    )


@router.get("/active/all", response_model=AllTasksResponse)
def get_all_active_tasks() -> AllTasksResponse:
    return AllTasksResponse(
        projects=[
            ProjectTasksResponse(project=item.project, tasks=list(item.tasks))
            for item in list_all_active_project_tasks(load_manifest())
        ]
    )


@router.get("/active/{task_id}", response_model=TaskRecord)
def get_active_task(task_id: str, project: str = "whub-dev") -> TaskRecord:
    return load_active_project_task(load_manifest(), project, task_id)


@router.get("/{task_id}", response_model=TaskRecord)
def get_task(task_id: str, project: str = "whub-dev") -> TaskRecord:
    return load_project_task(load_manifest(), project, task_id)
