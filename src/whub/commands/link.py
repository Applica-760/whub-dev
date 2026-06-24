"""whub link — create symlinks declared in the manifest."""
from __future__ import annotations
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.health import inspect_resource
from whub.models import Manifest, SymlinkResource

_GITIGNORE_MARKER = "# whub link (auto-generated)"

def _update_gitignore(m: Manifest, projects) -> None:
    gitignore = m.workspace_root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""

    top_dirs = sorted({
        project.resource.workspace_path.split("/")[0]
        for project in projects
        if isinstance(project.resource, SymlinkResource)
    })
    block = _GITIGNORE_MARKER + "\n" + "\n".join(top_dirs) + "\n"

    if _GITIGNORE_MARKER in existing:
        start = existing.index(_GITIGNORE_MARKER)
        rest_start = existing.find("\n\n", start)
        before = existing[:start]
        after = existing[rest_start:] if rest_start != -1 else ""
        text = before.rstrip("\n") + "\n\n" + block + after.lstrip("\n")
    else:
        text = existing.rstrip("\n") + "\n\n" + block

    gitignore.write_text(text)

@click.command()
@click.pass_context
def link(ctx: click.Context) -> None:
    """Create symlinks declared in the manifest."""
    m = get_manifest(ctx)
    created = skipped = warnings = 0
    projects = [
        project for project in m.projects
        if isinstance(project.resource, SymlinkResource)
    ]

    for project in projects:
        r = project.resource
        if not isinstance(r, SymlinkResource):
            continue
        target = m.resolve_path(r.workspace_path)
        source = Path(r.source).expanduser()
        health = inspect_resource(r, m)

        if health.state == "ok":
            click.echo(f"  skip  {project.name}")
            skipped += 1
        elif health.state != "missing":
            detail = f" ({health.detail})" if health.detail else ""
            click.echo(f"  WARN  {project.name}: {health.state}{detail}")
            warnings += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source)
            result = inspect_resource(r, m)
            if result.state == "ok":
                click.echo(f"  link  {project.name}: {target} -> {source}")
                created += 1
            else:
                detail = f" ({result.detail})" if result.detail else ""
                click.echo(f"  WARN  {project.name}: {result.state}{detail}")
                warnings += 1

    _update_gitignore(m, projects)
    click.echo(f"\n  done: {created} created, {skipped} skipped, {warnings} warnings")
