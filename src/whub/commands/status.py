"""whub status — show health of all resources."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.core.context import current_context
from whub.services.status import collect_status
from whub.utils.render import render_table


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show health of all resources."""
    manifest = get_manifest(ctx)
    report = collect_status(manifest, current_context().workspace_root)
    statuses = report.resources
    worktrees = report.worktrees
    if not statuses and not worktrees:
        click.echo("  (no resources)")
        return

    if statuses:
        render_table(
            [
                (item.project, item.state, item.type, item.mount, item.tmux, item.git)
                for item in statuses
            ],
            headers=("project", "state", "type", "mount", "tmux", "git"),
            right_align={5},
        )

    diagnostics = [item for item in worktrees if item.diagnostics]
    if worktrees:
        click.echo()
        suffix = "ok" if not diagnostics else f"{len(diagnostics)} diagnostic"
        click.echo(f"worktrees: {len(worktrees)} registered, {suffix}")
    for item in diagnostics:
        identity = (
            f"{item.parent_project}/{item.task_id}"
            if item.parent_project is not None and item.task_id is not None
            else "invalid registration"
        )
        for diagnostic in item.diagnostics:
            click.echo(f"  {identity}: {diagnostic}")

    if report.unhealthy:
        raise click.exceptions.Exit(1)
