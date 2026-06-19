"""whub CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click

from whub.manifest import load_manifest


@click.group()
@click.option(
    "--manifest",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to manifest.yaml (default: ./manifest.yaml)",
)
@click.pass_context
def main(ctx: click.Context, manifest: Path | None) -> None:
    """workspace-hub: manage workspaces from a single manifest."""
    ctx.ensure_object(dict)
    ctx.obj["manifest_path"] = manifest


def _load(ctx: click.Context):
    return load_manifest(ctx.obj["manifest_path"])


# ── Setup ──


@main.command()
@click.pass_context
def link(ctx: click.Context) -> None:
    """Create symlinks declared in the manifest."""
    click.echo("link: not yet implemented")


@main.command()
@click.argument("host", required=False)
@click.pass_context
def mount(ctx: click.Context, host: str | None) -> None:
    """Mount remote directories via sshfs."""
    click.echo("mount: not yet implemented")


@main.command()
@click.argument("host", required=False)
@click.pass_context
def unmount(ctx: click.Context, host: str | None) -> None:
    """Unmount remote directories."""
    click.echo("unmount: not yet implemented")


# ── Daily ──


@main.command()
@click.argument("resource")
@click.argument("command", required=False)
@click.pass_context
def cd(ctx: click.Context, resource: str, command: str | None) -> None:
    """Jump to a resource (local cd or SSH)."""
    click.echo("cd: not yet implemented")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show status of all resources."""
    m = _load(ctx)
    for r in m.resources:
        hub_path = Path(r.path)
        if r.type == "symlink":
            exists = hub_path.is_symlink() or hub_path.exists()
            mark = "ok" if exists else "missing"
        elif r.type == "mount":
            exists = hub_path.is_mount()
            mark = "mounted" if exists else "not mounted"
        else:
            mark = "?"
        click.echo(f"  {r.name:20s}  {r.type:8s}  {mark}")


# ── Rules ──


@main.group()
def rules() -> None:
    """Manage agent rules."""


@rules.command("deploy")
@click.pass_context
def rules_deploy(ctx: click.Context) -> None:
    """Deploy agent rules to target resources."""
    click.echo("rules deploy: not yet implemented")


# ── Diagnostics ──


@main.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Check manifest and resource health."""
    click.echo("doctor: not yet implemented")
