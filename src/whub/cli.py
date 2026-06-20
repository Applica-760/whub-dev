"""whub CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click

from whub.commands.boot import boot
from whub.commands.cd import cd
from whub.commands.doctor import doctor
from whub.commands.link import link
from whub.commands.mount import mount, unmount
from whub.commands.shell_init import shell_init
from whub.commands.status import status


@click.group()
@click.option(
    "--manifest",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to manifest.yaml (default: ./manifest.yaml)",
)
@click.pass_context
def main(ctx: click.Context, manifest: Path | None) -> None:
    """workspace-hub: manage workspaces from a single manifest."""
    ctx.ensure_object(dict)
    ctx.obj["manifest_path"] = manifest


main.add_command(link)
main.add_command(mount)
main.add_command(unmount)
main.add_command(cd)
main.add_command(status)
main.add_command(boot)
main.add_command(doctor)
main.add_command(shell_init)
