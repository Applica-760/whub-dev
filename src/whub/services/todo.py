"""Todo operations shared by CLI and web adapters."""

from __future__ import annotations

from datetime import date

import yaml
from whub.core.context import WhubContext, current_context
from whub.models import Manifest
from whub.models.todo import PRIORITIES, Todo, Todos
from whub.services.errors import NotFoundError, ServiceError


def _priority_rank(item: Todo) -> int:
    return PRIORITIES.index(item.priority)


def _pending_sort_key(item: Todo) -> tuple[bool, date, int, int]:
    return (
        item.due_date is None,
        item.due_date or date.max,
        _priority_rank(item),
        item.id,
    )


def _completed_sort_key(item: Todo) -> tuple[date, int]:
    return (item.done_at or date.max, item.id)


def load_todos(context: WhubContext | None = None) -> Todos:
    """Load todos from the current Hub context."""
    context = context or current_context()
    text = context.read_todo_text()
    if text is None:
        return Todos()
    data = yaml.safe_load(text)
    if not data:
        return Todos()
    return Todos.model_validate(data)


def save_todos(todos: Todos, context: WhubContext | None = None) -> None:
    """Persist todos in the current Hub context."""
    context = context or current_context()
    context.write_todo_text(
        yaml.safe_dump(
            todos.model_dump(mode="json", exclude_none=True),
            allow_unicode=True,
            sort_keys=False,
        ),
    )


def list_pending() -> list[Todo]:
    """Return pending todos in display order."""
    return sorted(load_todos().pending, key=_pending_sort_key)


def list_completed() -> list[Todo]:
    """Return completed todos in display order."""
    return sorted(load_todos().completed, key=_completed_sort_key)


def add_todo(
    manifest: Manifest,
    title: str,
    project: str | None,
    priority: str,
    due_date: date | None,
) -> Todo:
    """Create and persist a todo."""
    if project is not None and manifest.resolve_project(project) is None:
        raise ServiceError(f"unknown project: {project}")

    todos = load_todos()
    item = Todo(
        id=max((todo.id for todo in todos.todos), default=0) + 1,
        title=title,
        project=project,
        priority=priority,
        created_at=date.today(),
        due_date=due_date,
    )
    todos.todos.append(item)
    save_todos(todos)
    return item


def complete_todo(todo_id: int) -> Todo:
    """Mark a pending todo as completed and persist it."""
    todos = load_todos()
    item = next((todo for todo in todos.todos if todo.id == todo_id), None)
    if item is None:
        raise NotFoundError(f"todo not found: {todo_id}")
    if item.done:
        raise ServiceError(f"already done: {todo_id}")

    item.done = True
    item.done_at = date.today()
    save_todos(todos)
    return item


def remove_todo(todo_id: int) -> Todo:
    """Remove a todo and persist the remaining collection."""
    todos = load_todos()
    item = next((todo for todo in todos.todos if todo.id == todo_id), None)
    if item is None:
        raise NotFoundError(f"todo not found: {todo_id}")

    todos.todos.remove(item)
    save_todos(todos)
    return item
