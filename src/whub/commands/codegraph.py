"""whub codegraph — initialize CodeGraph for configured Project resources."""

from __future__ import annotations

import shlex
import shutil
import subprocess

import click

from whub.commands import get_manifest
from whub.core.remote import run_ssh_command
from whub.core.target import TargetItem, on_targets
from whub.models import Manifest, Project, RemoteResource, SymlinkResource
from whub.utils.process import format_process_error


def _init_local_codegraph(resource: SymlinkResource, project: Project) -> None:
    target = resource._resolved_workspace_path
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


def _init_remote_codegraph(resource: RemoteResource, project: Project) -> None:
    try:
        run_ssh_command(
            resource._resolved_host,
            f'source "$HOME/.nvm/nvm.sh" 2>/dev/null;'
            f" codegraph init {shlex.quote(resource.remote_path)}",
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


def _collect_codegraph_targets(manifest: Manifest) -> list[TargetItem[Project]]:
    return [
        TargetItem(project.resource, project)
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
