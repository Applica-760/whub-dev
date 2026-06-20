"""whub link — create symlinks declared in the manifest."""

from __future__ import annotations

from pathlib import Path

import click

from whub.commands import get_manifest

_GITIGNORE_MARKER = "# whub link (auto-generated)"


def _update_gitignore(m) -> None:
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


@click.command()
@click.pass_context
def link(ctx: click.Context) -> None:
    """Create symlinks declared in the manifest."""
    m = get_manifest(ctx)
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
