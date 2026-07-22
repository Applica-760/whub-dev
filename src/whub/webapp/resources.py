"""Resolve packaged and development Web app resources."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


class AppResourceError(Exception):
    """Raised when a required Web app resource cannot be resolved."""


def packaged_app_dist() -> Path:
    """Return the filesystem-backed Web app distribution in the Whub package."""
    resource = files("whub").joinpath("webapp", "dist")
    if not isinstance(resource, Path) or not (resource / "index.html").is_file():
        raise AppResourceError("web app distribution is missing from this Whub package")
    return resource


def development_app_source() -> Path:
    """Return the Web app source from the checkout providing this Whub module."""
    source_file = Path(__file__).resolve()
    try:
        checkout = source_file.parents[3]
    except IndexError as error:
        raise AppResourceError("Whub development checkout is unavailable") from error

    expected_source = checkout / "src" / "whub" / "webapp" / source_file.name
    app_dir = checkout / "app"
    if (
        source_file != expected_source
        or not (checkout / "pyproject.toml").is_file()
        or not (app_dir / "package.json").is_file()
    ):
        raise AppResourceError("Whub development checkout is unavailable")
    return app_dir
