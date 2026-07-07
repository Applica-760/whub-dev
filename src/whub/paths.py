"""Path resolution for whub root, config, and data files."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

import click


def whub_root() -> Path:
    env = os.environ.get("WHUB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return _package_workspace_root()


def whub_config_dir() -> Path:
    return whub_root() / ".whub"


def whub_config_path() -> Path:
    return whub_config_dir() / "config.toml"


def whub_data_dir() -> Path:
    env = os.environ.get("WHUB_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()

    config_path = whub_config_path()
    if not config_path.exists():
        raise click.ClickException(
            f"whub data_dir is not configured; run `whub init <data_dir>` "
            f"to create {config_path}"
        )

    try:
        data = tomllib.loads(config_path.read_text())
    except tomllib.TOMLDecodeError as error:
        raise click.ClickException(f"invalid whub config: {config_path}: {error}") from error

    value = data.get("data_dir")
    if not isinstance(value, str) or not value:
        raise click.ClickException(f"whub config missing data_dir: {config_path}")
    return Path(value).expanduser().resolve()


def manifest_path() -> Path:
    return whub_data_dir() / "manifest.yaml"


def todo_path() -> Path:
    return whub_data_dir() / "todos.yaml"


def downloads_dir() -> Path:
    return whub_data_dir() / "downloads"


def _package_workspace_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "whub").exists():
            return parent
    return current.parents[2]
