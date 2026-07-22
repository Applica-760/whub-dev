"""Read immutable Whub release metadata from the installed package."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version as package_version
from importlib.resources import files
import json
import re

import click


class ReleaseMetadataError(Exception):
    """Raised when packaged release metadata is invalid."""


@dataclass(frozen=True)
class ReleaseInfo:
    """Identity of the Whub package providing the current process."""

    package_version: str
    source_commit: str | None

    @property
    def release_id(self) -> str:
        if self.source_commit is None:
            return f"{self.package_version}+source"
        return f"{self.package_version}+g{self.source_commit[:8]}"

    @property
    def display(self) -> str:
        if self.source_commit is None:
            return f"{self.package_version} (source checkout)"
        return f"{self.package_version} (commit {self.source_commit})"


def current_release() -> ReleaseInfo:
    """Return package version and optional build-time source commit."""
    installed_version = package_version("whub")
    resource = files("whub").joinpath("_build.json")
    if not resource.is_file():
        return ReleaseInfo(installed_version, None)

    try:
        data = json.loads(resource.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseMetadataError("invalid packaged release metadata") from error
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ReleaseMetadataError("invalid packaged release metadata schema")
    if data.get("package_version") != installed_version:
        raise ReleaseMetadataError("packaged release metadata version mismatch")
    commit = data.get("source_commit")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ReleaseMetadataError("invalid packaged release source_commit")
    return ReleaseInfo(installed_version, commit)


def release_version_option(program_name: str):
    """Add a shared eager --version option to a Click command."""

    def show_version(
        context: click.Context,
        parameter: click.Parameter,
        value: bool,
    ) -> None:
        del parameter
        if not value or context.resilient_parsing:
            return
        try:
            info = current_release()
        except ReleaseMetadataError as error:
            raise click.ClickException(str(error)) from error
        click.echo(f"{program_name}, version {info.display}")
        context.exit()

    return click.option(
        "--version",
        is_flag=True,
        is_eager=True,
        expose_value=False,
        callback=show_version,
        help="Show the installed Whub release and exit.",
    )
