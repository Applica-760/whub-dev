"""Todo JSON API."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel

from whub.services.manifest import load_manifest
from whub.models.todo import Priority, Todo
from whub.services.todo import (
    add_todo,
    complete_todo,
    list_completed,
    list_pending,
    remove_todo,
)


router = APIRouter(prefix="/api/todos")


class TodoResponse(BaseModel):
    id: int
    title: str
    project: str | None
    priority: Priority
    done: bool
    created_at: date
    due_date: date | None
    done_at: date | None


class TodoListResponse(BaseModel):
    pending: list[TodoResponse]
    completed: list[TodoResponse]


class CreateTodoRequest(BaseModel):
    title: str
    project: str | None = None
    priority: Priority = "none"
    due_date: date | None = None


class CompleteTodoRequest(BaseModel):
    done: Literal[True]


def _todo_response(item: Todo) -> TodoResponse:
    return TodoResponse(**item.model_dump())


@router.get("", response_model=TodoListResponse)
def get_todos() -> TodoListResponse:
    return TodoListResponse(
        pending=[_todo_response(item) for item in list_pending()],
        completed=[_todo_response(item) for item in list_completed()],
    )


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(request: CreateTodoRequest) -> TodoResponse:
    item = add_todo(
        load_manifest(),
        request.title,
        request.project,
        request.priority,
        request.due_date,
    )
    return _todo_response(item)


@router.patch("/{todo_id}", response_model=TodoResponse)
def complete_todo_by_id(
    todo_id: int,
    request: CompleteTodoRequest,
) -> TodoResponse:
    del request
    return _todo_response(complete_todo(todo_id))


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int) -> None:
    remove_todo(todo_id)
