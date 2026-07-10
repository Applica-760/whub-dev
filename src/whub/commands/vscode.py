"""whub vscode — generate VS Code exclusion settings."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from whub.commands import get_manifest
from whub.models import Manifest, RemoteResource, SymlinkResource
from whub.paths import whub_root


def _excluded_paths(manifest: Manifest) -> list[str]:
    paths: list[str] = []
    for project in manifest.projects:
        resource = project.resource
        if isinstance(resource, SymlinkResource):
            paths.append(f"{resource.workspace_path}/**")
        elif isinstance(resource, RemoteResource) and resource.mount:
            paths.append(f"{resource.workspace_path}/**")
    return sorted(paths)


def _build_settings(manifest: Manifest) -> dict[str, Any]:
    paths = _excluded_paths(manifest)
    exclusions = {path: True for path in paths}
    return {
        "files.watcherExclude": exclusions,
        "search.exclude": exclusions,
        "python.analysis.exclude": paths,
    }


def _load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise click.ClickException(f"VS Code settings is not a file: {path}")
    try:
        settings = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise click.ClickException(f"invalid VS Code settings JSON: {path}: {error}") from error
    if not isinstance(settings, dict):
        raise click.ClickException(f"VS Code settings must be a JSON object: {path}")
    return settings


def _merge_settings(existing: dict[str, Any], manifest: Manifest) -> dict[str, Any]:
    return {**existing, **_build_settings(manifest)}


@click.command()
@click.pass_context
def vscode(ctx: click.Context) -> None:
    """Generate VS Code exclusions from manifest resources."""
    settings_path = whub_root() / ".vscode" / "settings.json"
    settings = _merge_settings(_load_settings(settings_path), get_manifest(ctx))
    content = json.dumps(settings, ensure_ascii=False, indent=2) + "\n"

    if settings_path.exists() and settings_path.read_text() == content:
        click.echo(f"  skip  {settings_path}")
        return

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(content)
    click.echo(f"  write {settings_path}")
