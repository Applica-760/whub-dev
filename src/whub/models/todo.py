"""Personal todo schemas."""

from __future__ import annotations
from datetime import date
from typing import Literal, get_args
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Priority = Literal["red", "yellow", "blue", "none"]
PRIORITIES: list[str] = list(get_args(Priority))

PRIORITY_EMOJI: dict[str | None, str] = {
    "red": "🔴",
    "yellow": "🟡",
    "blue": "🔵",
    "none": "─",
    None: "─",
}


class Todo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    title: str
    project: str | None = None
    priority: Priority = "none"
    done: bool = False
    created_at: date
    due_date: date | None = None
    done_at: date | None = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be empty")
        return value

    @field_validator("project")
    @classmethod
    def _validate_project(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("project must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_completion(self) -> Todo:
        if self.done != (self.done_at is not None):
            raise ValueError("done and done_at must be set together")
        return self


class Todos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    todos: list[Todo] = Field(default_factory=list)

    @property
    def pending(self) -> list[Todo]:
        return [t for t in self.todos if not t.done]

    @property
    def completed(self) -> list[Todo]:
        return [t for t in self.todos if t.done]

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> Todos:
        ids = [todo.id for todo in self.todos]
        duplicates = sorted({todo_id for todo_id in ids if ids.count(todo_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate todo ids: {', '.join(map(str, duplicates))}")
        return self
