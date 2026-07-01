"""whub roadmap — append a raw memo to a project's roadmap."""
from __future__ import annotations
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.models import (
    Manifest,
    RemoteResource,
    SymlinkResource,
    project_names,
    workspace_hub_resource,
)
from whub.target import TargetItem, on_targets, resolve_project_resource

_MARKER_START = "<!-- hub:roadmap:appended:start -->"
_MARKER_END = "<!-- hub:roadmap:appended:end -->"


def _seed(project_name: str) -> str:
    return (
        f"# {project_name} Roadmap\n\n"
        f"{_MARKER_START}\n{_MARKER_END}\n"
    )


def _insert_memo(content: str, memo: str) -> str:
    if content.count(_MARKER_START) != 1 or content.count(_MARKER_END) != 1:
        raise click.ClickException("roadmap markers are missing or duplicated")
    start, end = content.index(_MARKER_START), content.index(_MARKER_END)
    if start > end:
        raise click.ClickException("roadmap start marker appears after end marker")
    return content[:end] + f"- {memo}\n" + content[end:]


def _resolve_target_resource(
    manifest: Manifest, project: str, data: tuple[str, str]
) -> TargetItem[tuple[str, str]]:
    proj = manifest.resolve_project(project)
    if proj is not None and proj.resource is None and proj.name == "workspace-hub":
        return TargetItem(workspace_hub_resource(), data)
    return TargetItem(resolve_project_resource(manifest, project), data)


def _local(resource: SymlinkResource, data: tuple[str, str]) -> None:
    name, memo = data
    root = Path(resource.source)
    if not root.exists():
        raise click.ClickException(f"resource source does not exist: {root}")
    path = root / "docs" / "roadmap.md"
    content = path.read_text() if path.exists() else _seed(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_insert_memo(content, memo))
    click.echo(f"  roadmap {name}: {memo}")


def _remote(resource: RemoteResource, data: tuple[str, str]) -> None:
    """remoteはPhase 4で対応。今は未対応を通知するだけ。"""
    del resource, data
    click.echo("  remote roadmap is not supported yet")


@click.command()
@click.argument("project", shell_complete=project_names)
@click.argument("text", nargs=-1, required=True)
@click.pass_context
def roadmap(ctx: click.Context, project: str, text: tuple[str, ...]) -> None:
    """Append a raw memo to a project's roadmap."""
    manifest = get_manifest(ctx)
    memo = " ".join(text).strip()
    if not memo:
        raise click.UsageError("memo text is required")
    target = _resolve_target_resource(manifest, project, (project, memo))
    on_targets([target], local=_local, remote=_remote)
