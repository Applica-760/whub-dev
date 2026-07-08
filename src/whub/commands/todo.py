"""whub todo — manage personal todos."""
from __future__ import annotations
import re
from datetime import date
import click
from whub.commands import get_manifest
from whub.models import project_names
from whub.models.todo import PRIORITIES, PRIORITY_EMOJI, Todo, load_todos, save_todos
from whub.utils.render import TableCell, render_table


def _project_names(ctx, param, incomplete: str) -> list[str]:
    none = ["none"] if "none".startswith(incomplete) else []
    return none + project_names(ctx, param, incomplete)


def _format_date_cell(value: date | None, *, urgent: bool) -> object:
    if value is None:
        return "-"
    text = value.isoformat()
    if not urgent:
        return text
    remaining_days = (value - date.today()).days
    if remaining_days <= 3:
        return TableCell(text, fg="red")
    if remaining_days <= 7:
        return TableCell(text, fg="yellow")
    return text


def _parse_due_date(value: str | None, *, today: date | None = None) -> date | None:
    if value is None:
        return None

    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)

        if re.fullmatch(r"\d{4}", value):
            current = today or date.today()
            month = int(value[:2])
            day = int(value[2:])
            candidate = date(current.year, month, day)
            if candidate < current:
                candidate = date(current.year + 1, month, day)
            return candidate
    except ValueError as error:
        raise click.BadParameter(
            "expected valid YYYY-MM-DD or MMDD",
            param_hint="due_date",
        ) from error

    raise click.BadParameter("expected YYYY-MM-DD or MMDD", param_hint="due_date")


def _render_list(
    items: list[Todo],
    date_label: str,
    date_fn,
    *,
    empty: str,
    urgent_dates: bool = False,
) -> None:
    if not items:
        click.echo(f"  ({empty})")
        return
    rows = []
    previous_priority = None
    for item in items:
        if previous_priority is not None and item.priority != previous_priority:
            rows.append(())
        project = item.project or "-"
        d = date_fn(item)
        rows.append((
            item.id,
            PRIORITY_EMOJI[item.priority],
            item.title,
            project,
            _format_date_cell(d, urgent=urgent_dates),
        ))
        previous_priority = item.priority
    render_table(rows, headers=("id", "pri", "title", "project", date_label), right_align={0})


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


# ── CLI ───────────────────────────────────────────────────────────
@click.group(invoke_without_command=True)
@click.option("-a", is_flag=True, help="Include completed todos.")
@click.pass_context
def todo(ctx: click.Context, a: bool) -> None:
    """Manage personal todos."""
    if ctx.invoked_subcommand is not None:
        return
    todos = load_todos()
    pending = sorted(todos.pending, key=_pending_sort_key)
    _render_list(
        pending,
        "due",
        lambda t: t.due_date,
        empty="no pending todos",
        urgent_dates=True,
    )
    if a:
        click.echo()
        click.echo("  done:")
        completed = sorted(todos.completed, key=_completed_sort_key)
        _render_list(completed, "done", lambda t: t.done_at, empty="no completed todos")


@todo.command()
@click.argument("title")
@click.argument("project", shell_complete=_project_names)
@click.argument("priority", type=click.Choice(PRIORITIES))
@click.argument("due_date", required=False)
@click.pass_context
def add(
    ctx: click.Context,
    title: str,
    project: str,
    priority: str,
    due_date: str | None,
) -> None:
    """Add a todo."""
    project_name = None if project == "none" else project
    if project_name is not None:
        if get_manifest(ctx).resolve_project(project_name) is None:
            raise click.UsageError(f"unknown project: {project_name}")

    todos = load_todos()
    todo_id = max((item.id for item in todos.todos), default=0) + 1
    item = Todo(
        id=todo_id,
        title=title,
        project=project_name,
        priority=priority,
        created_at=date.today(),
        due_date=_parse_due_date(due_date),
    )
    todos.todos.append(item)
    save_todos(todos)
    click.echo(f"  added {item.id}: {item.title}")


@todo.command()
@click.argument("todo_id", type=int)
def done(todo_id: int) -> None:
    """Mark a todo as done."""
    todos = load_todos()
    item = next((t for t in todos.todos if t.id == todo_id), None)
    if item is None:
        raise click.UsageError(f"todo not found: {todo_id}")
    if item.done:
        raise click.UsageError(f"already done: {todo_id}")
    item.done = True
    item.done_at = date.today()
    save_todos(todos)
    click.echo(f"  done {item.id}: {item.title}")


@todo.command()
@click.argument("todo_id", type=int)
def rm(todo_id: int) -> None:
    """Remove a todo."""
    todos = load_todos()
    item = next((t for t in todos.todos if t.id == todo_id), None)
    if item is None:
        raise click.UsageError(f"todo not found: {todo_id}")
    todos.todos.remove(item)
    save_todos(todos)
    click.echo(f"  removed {item.id}: {item.title}")
