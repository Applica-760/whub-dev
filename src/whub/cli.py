"""whub CLI entry point."""
from __future__ import annotations
from typing import Any

import click

from whub.commands.app import app
from whub.commands.backlog import backlog
from whub.commands.boot import boot
from whub.commands.cd import cd, shell_init
from whub.commands.fetch import fetch
from whub.commands.init import init
from whub.commands.knowledge import knowledge
from whub.commands.link import link
from whub.commands.mount import mount, unmount
from whub.commands.run import run
from whub.commands.session import session
from whub.commands.status import status
from whub.commands.todo import todo
from whub.commands.vscode import vscode
from whub.core.paths import PathError


class WhubGroup(click.Group):
    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except PathError as error:
            raise click.ClickException(str(error)) from error


@click.group(cls=WhubGroup)
def main() -> None:
    """workspace-hub: manage workspaces from a single manifest."""

main.add_command(link)
main.add_command(mount)
main.add_command(unmount)
main.add_command(cd)
main.add_command(run)
main.add_command(session)
main.add_command(fetch)
main.add_command(init)
main.add_command(knowledge)
main.add_command(status)
main.add_command(boot)
main.add_command(shell_init)
main.add_command(todo)
main.add_command(backlog)
main.add_command(app)
main.add_command(vscode)
