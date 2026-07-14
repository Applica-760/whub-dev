"""wflow CLI entry point."""
from __future__ import annotations

import click

from whub.wflow.commands.task import task
from whub.wflow.commands.workflow import check


@click.group()
def main() -> None:
    """Manage declarative Workflows and task records."""


main.add_command(check)
main.add_command(task)
