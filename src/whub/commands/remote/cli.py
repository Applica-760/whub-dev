"""Remote-resource CLI command group."""

from __future__ import annotations

import click

from whub.commands.remote.mount import mount, unmount
from whub.commands.remote.run import run
from whub.commands.remote.session import session
from whub.commands.remote.transfer import get, put, rm


@click.group()
def remote() -> None:
    """Manage remote resources."""


remote.add_command(run)
remote.add_command(mount)
remote.add_command(unmount)
remote.add_command(get)
remote.add_command(put)
remote.add_command(rm)
remote.add_command(session)
