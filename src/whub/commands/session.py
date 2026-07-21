"""whub session — reserve and observe remote GUI sessions."""

from __future__ import annotations

import re
import subprocess

import click
import yaml

from whub.commands import get_manifest
from whub.models import project_names
from whub.services.errors import ServiceError
from whub.services.session import (
    build_follow_logs_command,
    clean_session,
    get_session,
    list_sessions,
    read_session_logs,
    reserve_session,
    write_session_handoff,
)
from whub.utils.render import render_table


_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def _invoke(operation):
    try:
        return operation()
    except ServiceError as error:
        raise click.ClickException(str(error)) from error


@click.group()
def session() -> None:
    """Reserve and observe remote GUI sessions."""


@session.command()
@click.argument("project", shell_complete=project_names)
@click.option("--task", help="Optional TASK-ID associated with this run.")
@click.pass_context
def reserve(ctx: click.Context, project: str, task: str | None) -> None:
    """Reserve one pending GUI session run."""
    run_id = _invoke(lambda: reserve_session(get_manifest(ctx), project, task))
    click.echo(f"reserved {project} {run_id}")
    click.echo(f"Linux GUI: bash .whub/session-launcher.sh {run_id}")


@session.command("ls")
@click.argument("project", shell_complete=project_names)
@click.pass_context
def list_command(ctx: click.Context, project: str) -> None:
    """List runs for PROJECT."""
    items = _invoke(lambda: list_sessions(get_manifest(ctx), project))
    render_table(
        [
            (
                item.run_id,
                item.task or "-",
                item.state,
                len(item.panes),
                item.updated_at,
            )
            for item in items
        ],
        headers=("run", "task", "state", "panes", "updated"),
        right_align={3},
    )


@session.command()
@click.argument("project", shell_complete=project_names)
@click.argument("run_id")
@click.pass_context
def show(ctx: click.Context, project: str, run_id: str) -> None:
    """Show one run descriptor."""
    item = _invoke(lambda: get_session(get_manifest(ctx), project, run_id))
    click.echo(
        yaml.safe_dump(
            item.model_dump(mode="json"), allow_unicode=True, sort_keys=False
        ).rstrip()
    )


@session.command()
@click.argument("project", shell_complete=project_names)
@click.argument("run_id")
@click.option("--pane", help="Pane ID or unique window name.")
@click.option("--follow", is_flag=True, help="Follow one pane transcript.")
@click.pass_context
def logs(
    ctx: click.Context, project: str, run_id: str, pane: str | None, follow: bool
) -> None:
    """Print or follow pane transcripts."""
    manifest = get_manifest(ctx)
    if not follow:
        click.echo(
            _ANSI.sub(
                "", _invoke(lambda: read_session_logs(manifest, project, run_id, pane))
            ),
            nl=False,
        )
        return
    command = _invoke(
        lambda: build_follow_logs_command(manifest, project, run_id, pane)
    )
    process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout is not None
        for line in process.stdout:
            click.echo(_ANSI.sub("", line), nl=False)
    except KeyboardInterrupt:
        process.terminate()
    finally:
        process.wait()


@session.command()
@click.argument("project", shell_complete=project_names)
@click.argument("run_id")
@click.pass_context
def clean(ctx: click.Context, project: str, run_id: str) -> None:
    """Delete one pending or finished run and its logs."""
    _invoke(lambda: clean_session(get_manifest(ctx), project, run_id))
    click.echo(f"cleaned {project} {run_id}")


@session.command()
@click.argument("project", shell_complete=project_names)
@click.argument("run_id")
@click.option("--purpose", required=True, help="Single-line purpose for this command.")
@click.pass_context
def handoff(ctx: click.Context, project: str, run_id: str, purpose: str) -> None:
    """Prepend a stdin command to PROJECT's copy-only handoff Markdown."""
    purpose = purpose.strip()
    if not purpose or "\n" in purpose or "\r" in purpose:
        raise click.UsageError("purpose must be one non-empty line")
    stream = click.get_text_stream("stdin")
    if stream.isatty():
        raise click.UsageError("command must be provided via stdin")
    command = stream.read()
    if not command.strip():
        raise click.UsageError("command input is required")
    _invoke(
        lambda: write_session_handoff(
            get_manifest(ctx), project, run_id, purpose, command
        )
    )
    click.echo(f"updated {project} .whub/handoff/commands.md for {run_id}")
