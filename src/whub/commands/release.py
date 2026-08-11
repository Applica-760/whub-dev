"""whub release — build operation release artifacts."""

from __future__ import annotations

from pathlib import Path

import click

from whub.services.errors import ServiceError
from whub.services.release.apply import apply_release
from whub.services.release.build import build_release
from whub.services.release.verify import verify_release


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
@click.option(
    "--source",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=True,
    help="Path to the whub development checkout.",
)
def deploy(source: Path) -> None:
    """Build, verify, and apply one operation release."""
    try:
        built = build_release(source)
        if not built.verified:
            verify_release(built.release_id)
        result = apply_release(built.release_id)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"deployed {result.release_id}: {result.release_path}")


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
