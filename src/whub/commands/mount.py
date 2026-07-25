"""whub mount / unmount — sshfs-based mounts for remote resources."""

from __future__ import annotations

import click

from whub.commands import get_manifest
from whub.models import project_names
from whub.services.errors import ServiceError
from whub.services.mount import MountResult, mount_targets, unmount_targets
from whub.utils.render import render_table


def _invoke(operation):
    try:
        return operation()
    except ServiceError as error:
        raise click.ClickException(str(error)) from error


def _echo_results(results: list[MountResult]) -> None:
    if not results:
        click.echo("  (no remote resources)")
        return
    render_table(
        [(item.status, item.name) for item in results],
        headers=("status", "project"),
    )
    if any(not item.ok for item in results):
        raise click.exceptions.Exit(1)


@click.command()
@click.argument("project", required=False, shell_complete=project_names)
@click.option(
    "--all",
    "-a",
    "include_all",
    is_flag=True,
    help="Include resources with mount=false.",
)
@click.pass_context
def mount(ctx: click.Context, project: str | None, include_all: bool) -> None:
    """Mount remote resources via sshfs."""
    results = _invoke(
        lambda: mount_targets(get_manifest(ctx), project, include_all=include_all)
    )
    _echo_results(results)


@click.command()
@click.option("--force", is_flag=True, help="Force unmount (for stale mounts).")
@click.pass_context
def unmount(ctx: click.Context, force: bool) -> None:
    """Unmount all remote resources."""
    results = _invoke(lambda: unmount_targets(get_manifest(ctx), force=force))
    _echo_results(results)
