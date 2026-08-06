"""Resolve Project-scoped Task storage locations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whub.services.errors import ServiceError
from whub.services.manifest import ResolvedManifest
from whub.services.project_content import resolve_project_content_root


TASKS_RELATIVE_PATH = Path("wflow/tasks")


@dataclass(frozen=True)
class ResolvedProjectTaskStorage:
    """Resolved read and write boundaries for one Project's Tasks."""

    active_root: Path
    history_root: Path
    archive_root: Path
    read_roots: tuple[Path, ...]
    id_roots: tuple[Path, ...]


def resolve_project_task_storage(
    manifest: ResolvedManifest, project: str
) -> ResolvedProjectTaskStorage:
    """Resolve active, history, and archive Task roots for PROJECT."""
    content_root = resolve_project_content_root(manifest, project)
    active_root = manifest.workspace_root / TASKS_RELATIVE_PATH / project
    history_root = content_root / "docs/tasks"
    archive_root = history_root / "done"

    for label, root in (
        ("Hub task", active_root),
        ("Project task history", history_root),
        ("Project task archive", archive_root),
    ):
        if root.exists() and not root.is_dir():
            raise ServiceError(f"{label} path is not a directory: {project}")

    return ResolvedProjectTaskStorage(
        active_root=active_root,
        history_root=history_root,
        archive_root=archive_root,
        read_roots=tuple(root for root in (active_root, archive_root) if root.is_dir()),
        id_roots=(history_root,) if history_root.is_dir() else (),
    )
