"""whub release — build operation release artifacts."""

from __future__ import annotations

from pathlib import Path

import click

from whub.services.errors import ServiceError
from whub.services.release import apply_release, build_release, verify_release


@click.group()
def release() -> None:
    """Build, verify, and apply operation releases."""


@release.command()
@click.option(
    "--source",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=True,
    help="Path to the whub development checkout.",
)
def build(source: Path) -> None:
    """Build one wheel into the operation release staging area."""
    try:
        result = build_release(source)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"built {result.release_id}: {result.wheel_path}")


@release.command()
@click.argument("release_id")
def verify(release_id: str) -> None:
    """Verify one staged release."""
    try:
        result = verify_release(release_id)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"verified {result.release_id}: {result.wheel_sha256}")


@release.command(name="apply")
@click.argument("release_id")
def apply(release_id: str) -> None:
    """Apply one verified release."""
    try:
        result = apply_release(release_id)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"applied {result.release_id}: {result.release_path}")
