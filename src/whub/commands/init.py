"""whub init — initialize a Whub context."""

from __future__ import annotations

import json
from pathlib import Path

import click

from whub.core.context import current_context


@click.command()
@click.option(
    "--workspace-root",
    required=True,
    type=click.Path(
        path_type=Path,
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    help="Workspace root recorded in ~/.whub/config.toml.",
)
@click.option("--force", is_flag=True, help="Replace existing whub config.")
def init(workspace_root: Path, force: bool) -> None:
    """Initialize the fixed user Whub context."""
    context = current_context()
    config_dir = context.directory
    config_path = context.config_path
    content = f"workspace_root = {json.dumps(str(workspace_root))}\n"

    if config_dir.is_symlink():
        if not force:
            raise click.ClickException(
                f"{config_dir} is a symlink; use --force to replace it with a config directory"
            )
        config_dir.unlink()
    if config_dir.exists() and not config_dir.is_dir():
        raise click.ClickException(f"{config_dir} exists and is not a directory")
    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists() and config_path.read_text() == content:
        click.echo(f"  skip  {config_path}")
        return
    if config_path.exists() and not force:
        raise click.ClickException(
            f"{config_path} already exists; use --force to replace it"
        )

    config_path.write_text(content)
    click.echo(f"  init  {config_path}")
