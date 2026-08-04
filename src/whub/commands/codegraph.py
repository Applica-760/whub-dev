"""whub codegraph — initialize CodeGraph for configured Project resources."""

from __future__ import annotations

import shlex
import shutil
import subprocess

import click

from whub.commands import get_manifest
from whub.core.remote import run_ssh_command
from whub.core.target import TargetItem, on_targets
from whub.models import Project, RemoteResource, SymlinkResource
from whub.services.manifest import ResolvedManifest
from whub.utils.process import format_process_error


def _init_local_codegraph(
    resource: SymlinkResource, data: tuple[ResolvedManifest, Project]
) -> None:
    manifest, project = data
    target = manifest.workspace_path(resource)
    if not target.exists():
        click.echo(f"  {'skip':6s}  {project.name} (not found)")
        return

    executable = shutil.which("codegraph")
    if executable is None:
        click.echo(f"  {'WARN':6s}  {project.name}: codegraph not found; skipped")
        return
    try:
        subprocess.run(
            [executable, "init", str(target)],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        click.echo(
            f"  {'WARN':6s}  {project.name}: CodeGraph init failed:"
            f" {format_process_error(error)}",
        )
        return
    click.echo(f"  {'init':6s}  {project.name} (CodeGraph)")


def _init_remote_codegraph(
    resource: RemoteResource, data: tuple[ResolvedManifest, Project]
) -> None:
    manifest, project = data
    try:
        run_ssh_command(
            manifest.remote_host(resource),
            f"codegraph init {shlex.quote(manifest.remote_path(resource))}",
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        click.echo(
            f"  {'WARN':6s}  {project.name}: CodeGraph init failed:"
            f" {format_process_error(error)}",
        )
        return
    click.echo(f"  {'init':6s}  {project.name} (CodeGraph)")


def _collect_codegraph_targets(
    manifest: ResolvedManifest,
) -> list[TargetItem[tuple[ResolvedManifest, Project]]]:
    return [
        TargetItem(project.resource, (manifest, project))
        for project in manifest.projects
        if project.resource is not None and project.resource.codegraph
    ]


@click.command()
@click.pass_context
def codegraph(ctx: click.Context) -> None:
    """Initialize CodeGraph for enabled Project resources."""
    targets = _collect_codegraph_targets(get_manifest(ctx))
    on_targets(
        targets,
        local=_init_local_codegraph,
        remote=_init_remote_codegraph,
    )
