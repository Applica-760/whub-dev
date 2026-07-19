"""whub todo — manage personal todos."""
from __future__ import annotations
import re
from datetime import date

import click

from whub.commands import get_manifest
from whub.models import project_names
from whub.models.todo import PRIORITIES, PRIORITY_EMOJI, Todo
from whub.services.errors import ServiceError
from whub.services.todo import (
    add_todo,
    complete_todo,
    list_completed,
    list_pending,
    remove_todo,
)
from whub.utils.render import TableCell, render_table


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


# ── CLI ───────────────────────────────────────────────────────────
@click.group(invoke_without_command=True)
@click.option("-a", is_flag=True, help="Include completed todos.")
@click.pass_context
def todo(ctx: click.Context, a: bool) -> None:
    """Manage personal todos."""
    if ctx.invoked_subcommand is not None:
        return
    pending = list_pending()
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
        completed = list_completed()
        _render_list(completed, "done", lambda t: t.done_at, empty="no completed todos")


@todo.command()
@click.argument("title")
@click.argument("priority", type=click.Choice(PRIORITIES))
@click.argument("due_date", required=False)
@click.option("--project", shell_complete=project_names)
@click.pass_context
def add(
    ctx: click.Context,
    title: str,
    priority: str,
    due_date: str | None,
    project: str | None,
) -> None:
    """Add a todo."""
    try:
        item = add_todo(
            get_manifest(ctx),
            title,
            project,
            priority,
            _parse_due_date(due_date),
        )
    except ServiceError as error:
        raise click.UsageError(str(error)) from error
    click.echo(f"  added {item.id}: {item.title}")


@todo.command()
@click.argument("todo_id", type=int)
def done(todo_id: int) -> None:
    """Mark a todo as done."""
    try:
        item = complete_todo(todo_id)
    except ServiceError as error:
        raise click.UsageError(str(error)) from error
    click.echo(f"  done {item.id}: {item.title}")


@todo.command()
@click.argument("todo_id", type=int)
def rm(todo_id: int) -> None:
    """Remove a todo."""
    try:
        item = remove_todo(todo_id)
    except ServiceError as error:
        raise click.UsageError(str(error)) from error
    click.echo(f"  removed {item.id}: {item.title}")
