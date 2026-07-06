"""whub init — connect a workspace to a whub data directory."""
from __future__ import annotations

from pathlib import Path

import click


@click.command()
@click.argument("data_dir", type=click.Path(path_type=Path))
@click.option("--force", is_flag=True, help="Replace an existing .whub symlink.")
def init(data_dir: Path, force: bool) -> None:
    """Connect .whub to DATA_DIR."""
    workspace = Path.cwd()
    target = workspace / ".whub"
    source = data_dir.expanduser().resolve()

    if not source.exists():
        raise click.ClickException(f"data directory does not exist: {source}")
    if not source.is_dir():
        raise click.ClickException(f"data path is not a directory: {source}")
    if not (source / "manifest.yaml").exists():
        raise click.ClickException(f"manifest.yaml not found in data directory: {source}")

    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.resolve() == source:
            click.echo(f"  skip  .whub -> {source}")
            return
        if not force:
            raise click.ClickException(
                ".whub already exists; use --force to replace an existing symlink"
            )
        if not target.is_symlink():
            raise click.ClickException(".whub exists and is not a symlink")
        target.unlink()

    target.symlink_to(source, target_is_directory=True)
    click.echo(f"  init  .whub -> {source}")
