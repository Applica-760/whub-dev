"""whub CLI entry point."""

from __future__ import annotations
from typing import Any

import click

from whub.commands.app import app
from whub.commands.agent import agent
from whub.commands.backlog import backlog
from whub.commands.cd import cd, shell_init
from whub.commands.codegraph import codegraph
from whub.commands.init import init
from whub.commands.link import link
from whub.commands.ls import ls
from whub.commands.remote.cli import remote
from whub.commands.release import release
from whub.commands.status import status
from whub.commands.task import task
from whub.commands.todo import todo
from whub.core.context import PathError
from whub.core import release as release_metadata


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
        info = release_metadata.current_release()
    except release_metadata.ReleaseMetadataError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"{context.command.name}, version {info.display}")
    context.exit()


class WhubGroup(click.Group):
    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except PathError as error:
            raise click.ClickException(str(error)) from error


@click.group(name="whub", cls=WhubGroup)
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=show_version,
    help="Show the installed Whub release and exit.",
)
def main() -> None:
    """workspace-hub: manage workspaces from a single manifest."""


main.add_command(link)
main.add_command(ls)
main.add_command(release)
main.add_command(cd)
main.add_command(remote)
main.add_command(init)
main.add_command(status)
main.add_command(codegraph)
main.add_command(shell_init)
main.add_command(todo)
main.add_command(backlog)
main.add_command(app)
main.add_command(agent)
main.add_command(task)
