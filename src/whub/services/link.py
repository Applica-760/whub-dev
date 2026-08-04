"""Create workspace links declared in a manifest."""

from __future__ import annotations

from pathlib import Path

from whub.core.health import inspect_symlink
from whub.models import SymlinkResource
from whub.services.manifest import ResolvedManifest
from whub.utils.managed_block import format_block, replace_or_prepend_block


_GITIGNORE_MARKERS = (
    "# whub link (auto-generated): start",
    "# whub link (auto-generated): end",
)
_LEGACY_GITIGNORE_MARKER = "# whub link (auto-generated)"
_GITIGNORE_ENTRIES = (".codegraph/", ".DS_Store", "._*", ".AppleDouble/")


def _update_gitignore(workspace_root: Path, legacy_link_paths: set[str]) -> None:
    gitignore = workspace_root / ".gitignore"
    existing = gitignore.read_text() if gitignore.exists() else None
    if (
        existing
        and _GITIGNORE_MARKERS[0] not in existing
        and _LEGACY_GITIGNORE_MARKER in existing
    ):
        lines = existing.splitlines()
        start = lines.index(_LEGACY_GITIGNORE_MARKER)
        end = start + 1
        while end < len(lines) and lines[end] in (
            set(_GITIGNORE_ENTRIES)
            | legacy_link_paths
            | {f"/{path}" for path in legacy_link_paths}
        ):
            end += 1
        existing = "\n".join(lines[:start] + lines[end:]) + "\n"
    entries = (*sorted(f"/{path}" for path in legacy_link_paths), *_GITIGNORE_ENTRIES)
    gitignore.write_text(
        replace_or_prepend_block(
            format_block(_GITIGNORE_MARKERS, "\n".join(entries)),
            existing,
            _GITIGNORE_MARKERS,
        )
    )


def create_links(manifest: ResolvedManifest, workspace_root: Path) -> list[str]:
    lines: list[str] = []
    created = skipped = warnings = 0
    legacy_link_paths: set[str] = set()
    for project in manifest.projects:
        resource = project.resource
        if not isinstance(resource, SymlinkResource):
            continue
        legacy_link_paths.add(resource.workspace_path.split("/")[0])
        target = manifest.workspace_path(resource)
        source = Path(resource.source).expanduser()
        health = inspect_symlink(resource, target)
        if health.state == "ok":
            lines.append(f"  skip  {project.name}")
            skipped += 1
        elif health.state != "missing":
            lines.append(
                f"  WARN  {project.name}: {health.state}{f' ({health.detail})' if health.detail else ''}"
            )
            warnings += 1
        else:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(source)
            except OSError as error:
                lines.append(f"  WARN  {project.name}: link failed: {error}")
                warnings += 1
                continue
            result = inspect_symlink(resource, target)
            if result.state == "ok":
                lines.append(f"  link  {project.name}: {target} -> {source}")
                created += 1
            else:
                lines.append(
                    f"  WARN  {project.name}: {result.state}{f' ({result.detail})' if result.detail else ''}"
                )
                warnings += 1
    _update_gitignore(workspace_root, legacy_link_paths)
    return [
        *lines,
        f"\n  done: {created} created, {skipped} skipped, {warnings} warnings",
    ]
