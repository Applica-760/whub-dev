"""Remove verified AppleDouble sidecars from a remote Project."""

from __future__ import annotations

import subprocess
from importlib.resources import files

import click

from whub.commands import get_manifest
from whub.core.remote import build_remote_exec_command, build_ssh_command
from whub.core.target import (
    TargetError,
    require_resource_type,
    resolve_project_resource,
)
from whub.models import RemoteResource, project_names
from whub.utils.apple_double import APPLE_DOUBLE_MAGIC, APPLE_DOUBLE_PREFIX


@click.command(name="cleanup-appledouble")
@click.option("--apply", is_flag=True, help="Delete listed sidecars after validation.")
@click.argument("project", shell_complete=project_names)
@click.pass_context
def cleanup_appledouble(ctx: click.Context, apply: bool, project: str) -> None:
    """List verified AppleDouble sidecars in a remote PROJECT."""
    manifest = get_manifest(ctx)
    try:
        resource = require_resource_type(
            resolve_project_resource(manifest, project), RemoteResource, project
        )
    except TargetError as error:
        raise click.ClickException(str(error)) from error

    remote_command = build_remote_exec_command(
        resource.remote_path,
        (
            "python3",
            "-c",
            files("whub").joinpath("assets", "cleanup_appledouble.py").read_text(),
            "--apply" if apply else "--list",
            APPLE_DOUBLE_PREFIX,
            APPLE_DOUBLE_MAGIC.hex(),
        ),
    )
    result = subprocess.run(build_ssh_command(resource._resolved_host, remote_command))
    ctx.exit(result.returncode)
