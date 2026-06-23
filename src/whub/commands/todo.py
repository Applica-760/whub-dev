"""whub todo — manage personal todos."""
from __future__ import annotations
from datetime import date, datetime
import click
from whub.models import load_manifest, resource_names
from whub.models.state import PRIORITY_EMOJI
from whub.models.state import PRIORITIES
from whub.models.todo import Todo, load_todos, save_todos
from whub.render import render_table

def _project_names(ctx, param, incomplete: str) -> list[str]:
    none = ["none"] if "none".startswith(incomplete) else []
    return none + resource_names(ctx, param, incomplete)


def _show_pending() -> None:
    pending = [item for item in load_todos().todos if not item.done]
    if not pending:
        click.echo("  (no pending todos)")
        return

    rows = []
    for item in pending:
        project = item.project or "-"
        due = item.due_date.isoformat() if item.due_date else "-"
        rows.append((
            item.id,
            PRIORITY_EMOJI[item.priority],
            item.title,
            project,
            "created",
            item.created_at.isoformat(),
            "due",
            due,
        ))

    for line in render_table(rows, right_align={0}):
        click.echo(f"  {line}")


@click.group(invoke_without_command=True)
@click.pass_context
def todo(ctx: click.Context) -> None:
    """Manage personal todos."""
    if ctx.invoked_subcommand is None:
        _show_pending()


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
        names = {resource.name for resource in load_manifest().all_resources}
        if project_name not in names:
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
