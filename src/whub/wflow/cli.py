"""wflow CLI entry point."""

from __future__ import annotations

import click

from whub.release import release_version_option
from whub.wflow.commands.task import task
from whub.wflow.commands.workflow import check


@click.group()
@release_version_option("wflow")
def main() -> None:
    """Manage declarative Workflows and task records."""


main.add_command(check)
main.add_command(task)
