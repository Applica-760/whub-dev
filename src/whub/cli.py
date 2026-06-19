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


_GITIGNORE_MARKER = "# whub link (auto-generated)"


def _update_gitignore(m):
    gitignore = m.root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""

    top_dirs = sorted({r.path.split("/")[0] for r in m.resources if r.type == "symlink"})
    block = _GITIGNORE_MARKER + "\n" + "\n".join(top_dirs) + "\n"

    if _GITIGNORE_MARKER in existing:
        before = existing[: existing.index(_GITIGNORE_MARKER)]
        text = before.rstrip("\n") + "\n\n" + block
    else:
        text = existing.rstrip("\n") + "\n\n" + block

    gitignore.write_text(text)


# ── Setup ──
@main.command()
@click.pass_context
def link(ctx: click.Context) -> None:
    """Create symlinks declared in the manifest."""
    m = _load(ctx)
    created = skipped = warnings = 0

    for r in m.resources:
        if r.type != "symlink":
            continue

        target = m.resolve_path(r.path)
        source = Path(r.source).expanduser()

        if not source.exists():
            click.echo(f"  WARN  {r.name}: source not found ({source})")
            warnings += 1
        elif target.is_symlink() and target.resolve() == source.resolve():
            click.echo(f"  skip  {r.name}")
            skipped += 1
        elif target.exists():
            click.echo(f"  WARN  {r.name}: exists but unexpected ({target})")
            warnings += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source)
            click.echo(f"  link  {r.name}: {target} -> {source}")
            created += 1

    _update_gitignore(m)
    click.echo(f"\n  done: {created} created, {skipped} skipped, {warnings} warnings")

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
        hub_path = m.resolve_path(r.path)
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
