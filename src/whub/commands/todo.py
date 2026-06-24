"""whub todo — manage personal todos."""
from __future__ import annotations
from datetime import date, datetime
import click
from whub.models import load_manifest, project_names
from whub.models.todo import PRIORITIES, PRIORITY_EMOJI, Todo, load_todos, save_todos
from whub.render import render_table


def _project_names(ctx, param, incomplete: str) -> list[str]:
    none = ["none"] if "none".startswith(incomplete) else []
    return none + project_names(ctx, param, incomplete)


def _render_list(items: list[Todo], date_label: str, date_fn, *, empty: str) -> None:
    if not items:
        click.echo(f"  ({empty})")
        return
    rows = []
    for item in items:
        project = item.project or "-"
        d = date_fn(item)
        rows.append((
            item.id,
            PRIORITY_EMOJI[item.priority],
            item.title,
            project,
            date_label,
            d.isoformat() if d else "-",
        ))
    render_table(rows, right_align={0})


@click.group(invoke_without_command=True)
@click.option("-a", is_flag=True, help="Include completed todos.")
@click.pass_context
def todo(ctx: click.Context, a: bool) -> None:
    """Manage personal todos."""
    if ctx.invoked_subcommand is not None:
        return
    todos = load_todos()
    _render_list(todos.pending, "due", lambda t: t.due_date, empty="no pending todos")
    if a:
        click.echo()
        click.echo("  done:")
        _render_list(todos.completed, "done", lambda t: t.done_at, empty="no completed todos")


@todo.command()
@click.argument("title")
@click.argument("project", shell_complete=_project_names)
@click.argument("priority", type=click.Choice(PRIORITIES))
@click.argument("due_date", required=False, type=click.DateTime(formats=["%Y-%m-%d"]))
def add(
    title: str,
    project: str,
    priority: str,
    due_date: datetime | None,
) -> None:
    """Add a todo."""
    project_name = None if project == "none" else project
    if project_name is not None:
        if load_manifest().resolve_project(project_name) is None:
            raise click.UsageError(f"unknown project: {project_name}")

    todos = load_todos()
    todo_id = max((item.id for item in todos.todos), default=0) + 1
    item = Todo(
        id=todo_id,
        title=title,
        project=project_name,
        priority=priority,
        created_at=date.today(),
        due_date=due_date.date() if due_date else None,
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
