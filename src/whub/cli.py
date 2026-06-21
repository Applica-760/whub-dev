"""whub CLI entry point."""

from __future__ import annotations

import click

from whub.commands.boot import boot
from whub.commands.cd import cd
from whub.commands.doctor import doctor
from whub.commands.link import link
from whub.commands.mount import mount, unmount
from whub.commands.shell_init import shell_init
from whub.commands.status import status


@click.group()
def main() -> None:
    """workspace-hub: manage workspaces from a single manifest."""


main.add_command(link)
main.add_command(mount)
main.add_command(unmount)
main.add_command(cd)
main.add_command(status)
main.add_command(boot)
main.add_command(doctor)
main.add_command(shell_init)
