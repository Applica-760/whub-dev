"""whub link — create symlinks declared in the manifest."""
from __future__ import annotations
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.health import inspect_resource

_GITIGNORE_MARKER = "# whub link (auto-generated)"

def _update_gitignore(m) -> None:
    gitignore = m.root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else ""

    top_dirs = sorted({
        resource.workspace_path.split("/")[0]
        for resource in m.resources.symlinks
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

    for r in m.resources.symlinks:
        target = m.resolve_path(r.workspace_path)
        source = Path(r.source).expanduser()
        health = inspect_resource(r, m)

        if health.state == "ok":
            click.echo(f"  skip  {r.name}")
            skipped += 1
        elif health.state != "missing":
            detail = f" ({health.detail})" if health.detail else ""
            click.echo(f"  WARN  {r.name}: {health.state}{detail}")
            warnings += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source)
            result = inspect_resource(r, m)
            if result.state == "ok":
                click.echo(f"  link  {r.name}: {target} -> {source}")
                created += 1
            else:
                detail = f" ({result.detail})" if result.detail else ""
                click.echo(f"  WARN  {r.name}: {result.state}{detail}")
                warnings += 1

    _update_gitignore(m)
    click.echo(f"\n  done: {created} created, {skipped} skipped, {warnings} warnings")
