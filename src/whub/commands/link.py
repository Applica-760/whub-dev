"""whub link — create symlinks declared in the manifest."""
from __future__ import annotations
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.health import inspect_symlink
from whub.models import SymlinkResource
from whub.paths import whub_root
from whub.utils.managed_block import format_block, replace_or_prepend_block

_GITIGNORE_MARKERS = (
    "# whub link (auto-generated): start",
    "# whub link (auto-generated): end",
)
_LEGACY_GITIGNORE_MARKER = "# whub link (auto-generated)"


def _update_gitignore(top_dirs: set[str]) -> None:
    if not top_dirs:
        return
    gitignore = Path.cwd() / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else None

    has_legacy_block = (
        existing
        and _GITIGNORE_MARKERS[0] not in existing
        and _LEGACY_GITIGNORE_MARKER in existing
    )
    if has_legacy_block:
        lines = existing.splitlines()
        start = lines.index(_LEGACY_GITIGNORE_MARKER)
        end = start + 1
        while end < len(lines) and lines[end] in top_dirs:
            end += 1
        existing = "\n".join(lines[:start] + lines[end:]) + "\n"

    block = format_block(_GITIGNORE_MARKERS, "\n".join(sorted(top_dirs)))
    text = replace_or_prepend_block(block, existing, _GITIGNORE_MARKERS)

    gitignore.write_text(text)


@click.command()
@click.pass_context
def link(ctx: click.Context) -> None:
    """Create symlinks declared in the manifest."""
    if Path.cwd() != whub_root():
        raise click.ClickException("whub link must be run from the workspace-hub root")
    m = get_manifest(ctx)
    created = skipped = warnings = 0
    top_dirs: set[str] = set()

    for project in m.projects:
        r = project.resource
        if not isinstance(r, SymlinkResource):
            continue
        top_dirs.add(r.workspace_path.split("/")[0])
        target = r._resolved_workspace_path
        source = Path(r.source).expanduser()
        health = inspect_symlink(r)

        if health.state == "ok":
            click.echo(f"  skip  {project.name}")
            skipped += 1
        elif health.state != "missing":
            detail = f" ({health.detail})" if health.detail else ""
            click.echo(f"  WARN  {project.name}: {health.state}{detail}")
            warnings += 1
        else:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(source)
            except OSError as error:
                click.echo(f"  WARN  {project.name}: link failed: {error}")
                warnings += 1
                continue
            result = inspect_symlink(r)
            if result.state == "ok":
                click.echo(f"  link  {project.name}: {target} -> {source}")
                created += 1
            else:
                detail = f" ({result.detail})" if result.detail else ""
                click.echo(f"  WARN  {project.name}: {result.state}{detail}")
                warnings += 1

    _update_gitignore(top_dirs)
    click.echo(f"\n  done: {created} created, {skipped} skipped, {warnings} warnings")
