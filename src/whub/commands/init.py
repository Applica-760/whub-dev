"""whub init — register a whub data directory."""
from __future__ import annotations

import json
from pathlib import Path

import click

from whub.core.paths import whub_config_dir, whub_config_path


@click.command()
@click.argument("data_dir", type=click.Path(path_type=Path))
@click.option("--force", is_flag=True, help="Replace existing whub config.")
def init(data_dir: Path, force: bool) -> None:
    """Register DATA_DIR in .whub/config.toml."""
    source = data_dir.expanduser().resolve()

    if not source.exists():
        raise click.ClickException(f"data directory does not exist: {source}")
    if not source.is_dir():
        raise click.ClickException(f"data path is not a directory: {source}")
    if not (source / "manifest.yaml").exists():
        raise click.ClickException(f"manifest.yaml not found in data directory: {source}")

    config_dir = whub_config_dir()
    config_path = whub_config_path()
    content = f"data_dir = {json.dumps(str(source))}\n"

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
        click.echo(f"  skip  {config_path} -> {source}")
        return
    if config_path.exists() and not force:
        raise click.ClickException(f"{config_path} already exists; use --force to replace it")

    config_path.write_text(content)
    click.echo(f"  init  {config_path} -> {source}")
