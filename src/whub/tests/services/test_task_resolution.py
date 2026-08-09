"""Project Task storage resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.models import Manifest
from whub.services.errors import ServiceError
from whub.services.manifest import ResolvedManifest, resolve_manifest
from whub.services.task_resolution import resolve_project_task_storage
from whub.tests.helpers import manifest_data


def _manifest(tmp_path: Path) -> tuple[ResolvedManifest, Path, Path]:
    hub_root = tmp_path / "workspace-hub"
    project_root = tmp_path / "project"
    hub_root.mkdir()
    project_root.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    return (
        resolve_manifest(Manifest.model_validate(data), hub_root),
        hub_root,
        project_root,
    )


def test_resolves_task_roots_and_existing_read_sets(tmp_path: Path) -> None:
    manifest, hub_root, project_root = _manifest(tmp_path)

    empty = resolve_project_task_storage(manifest, "local")

    assert empty.active_root == hub_root / "flow/tasks/local"
    assert empty.history_root == project_root / "docs/tasks"
    assert empty.archive_root == project_root / "docs/tasks/done"
    assert empty.read_roots == ()
    assert empty.id_roots == ()

    empty.active_root.mkdir(parents=True)
    empty.archive_root.mkdir(parents=True)

    populated = resolve_project_task_storage(manifest, "local")

    assert populated.read_roots == (populated.active_root, populated.archive_root)
    assert populated.id_roots == (populated.archive_root,)


@pytest.mark.parametrize("invalid_root", ["active", "history", "archive"])
def test_rejects_task_storage_paths_that_are_not_directories(
    tmp_path: Path, invalid_root: str
) -> None:
    manifest, hub_root, project_root = _manifest(tmp_path)
    roots = {
        "active": hub_root / "flow/tasks/local",
        "history": project_root / "docs/tasks",
        "archive": project_root / "docs/tasks/done",
    }
    root = roots[invalid_root]
    root.parent.mkdir(parents=True, exist_ok=True)
    root.write_text("not a directory")

    with pytest.raises(ServiceError, match="path is not a directory: local"):
        resolve_project_task_storage(manifest, "local")


def test_preserves_project_resource_resolution_errors(tmp_path: Path) -> None:
    manifest, _, project_root = _manifest(tmp_path)

    with pytest.raises(ServiceError, match="unknown project: missing"):
        resolve_project_task_storage(manifest, "missing")
    with pytest.raises(ServiceError, match="project has no resource: no-resource"):
        resolve_project_task_storage(manifest, "no-resource")

    project_root.rmdir()
    with pytest.raises(ServiceError, match="project resource is not available: local"):
        resolve_project_task_storage(manifest, "local")
