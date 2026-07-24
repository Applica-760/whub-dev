"""wflow CLI entry point."""

from __future__ import annotations

import click

from whub.core import release
from whub.wflow.commands.task import task
from whub.wflow.commands.workflow import check


def show_version(
    context: click.Context,
    parameter: click.Parameter,
    value: bool,
) -> None:
    """Show the installed release for this CLI."""
    del parameter
    if not value or context.resilient_parsing:
        return
    try:
        info = release.current_release()
    except release.ReleaseMetadataError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"{context.command.name}, version {info.display}")
    context.exit()


@click.group(name="wflow")
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=show_version,
    help="Show the installed Whub release and exit.",
)
def main() -> None:
    """Manage declarative Workflows and task records."""


main.add_command(check)
main.add_command(task)
