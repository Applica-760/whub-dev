"""whub init — initialize a Whub context."""

from __future__ import annotations

import click

from whub.core.context import WhubContext, invocation_path


@click.command()
@click.option("--force", is_flag=True, help="Replace existing whub config.")
def init(force: bool) -> None:
    """Create .whub/config.toml in the current directory."""
    context = WhubContext(invocation_path())
    config_dir = context.config_dir
    config_path = context.config_path

    if config_dir.is_symlink():
        if not force:
            raise click.ClickException(
                f"{config_dir} is a symlink; use --force to replace it with a config directory"
            )
        config_dir.unlink()
    if config_dir.exists() and not config_dir.is_dir():
        raise click.ClickException(f"{config_dir} exists and is not a directory")
    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists() and not config_path.read_text():
        click.echo(f"  skip  {config_path}")
        return
    if config_path.exists() and not force:
        raise click.ClickException(
            f"{config_path} already exists; use --force to replace it"
        )

    config_path.write_text("")
    click.echo(f"  init  {config_path}")
