"""Project Task runtime reader tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whub.models import Manifest
from whub.models.flow import TaskRuntime
from whub.services.errors import ServiceError
from whub.services.task.common import write_task, write_task_markdown
from whub.services.manifest import ResolvedManifest, resolve_manifest
from whub.services.task.project import list_project_tasks, load_project_task
from whub.tests.helpers import manifest_data


@pytest.fixture
def task_storage(
    tmp_path: Path,
) -> tuple[ResolvedManifest, Path, Path]:
    hub_root = tmp_path / "workspace-hub"
    project_root = tmp_path / "project"
    hub_root.mkdir()
    project_root.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    return (
        resolve_manifest(Manifest.model_validate(data), hub_root),
        hub_root / "flow/tasks/local",
        project_root / "docs/tasks/done",
    )


def _write_task(
    root: Path,
    filename: str,
    task_id: str,
    *,
    state: str = "draft",
    depends_on: list[str] | None = None,
    interruption_task_id: str | None = None,
    interruption_source_task_id: str | None = None,
    title: str = "Task",
) -> None:
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    write_task(
        path,
        TaskRuntime(
            schema_version=2,
            id=task_id,
            workflow="WF-001",
            state=state,
            depends_on=depends_on or [],
            interruption_task_id=interruption_task_id,
            interruption_source_task_id=interruption_source_task_id,
        ),
    )
    write_task_markdown(path, f"# {title}\n")


def _write_legacy_task(
    root: Path,
    filename: str,
    task_id: str,
    *,
    state: str = "draft",
    depends_on: list[str] | None = None,
    title: str = "Legacy Task",
) -> None:
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "task": {
                    "id": task_id,
                    "state": state,
                    "title": title,
                    "objective": "Legacy objective",
                    "depends_on": depends_on or [],
                },
            },
            allow_unicode=True,
            sort_keys=False,
        )
    )


def test_list_project_tasks_includes_active_and_archived_tasks(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(active_root, "active.yaml", "TASK-001", title="Active")
    _write_task(archive_root, "archived.yaml", "TASK-002", state="completed")

    tasks = list_project_tasks(manifest, "local")

    assert [(task.id, task.title) for task in tasks] == [
        ("TASK-001", "Active"),
        ("TASK-002", "Task"),
    ]


def test_load_project_task_falls_back_to_archive(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, _, archive_root = task_storage
    _write_task(archive_root, "archived.yaml", "TASK-002", state="completed")

    task = load_project_task(manifest, "local", "002")

    assert task.task.id == "TASK-002"


def test_project_task_list_derives_dependencies_across_active_and_archive(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(active_root, "dependent.yaml", "TASK-122", depends_on=["TASK-120"])
    _write_task(archive_root, "completed.yaml", "TASK-120", state="completed")

    tasks = {task.id: task for task in list_project_tasks(manifest, "local")}

    assert tasks["TASK-122"].ready is True
    assert tasks["TASK-122"].blocked_by == []


def test_project_task_reader_keeps_legacy_active_dependencies_and_markdown(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(archive_root, "completed.yaml", "TASK-120", state="completed")
    _write_legacy_task(
        active_root,
        "legacy.yaml",
        "TASK-121",
        depends_on=["TASK-120"],
        title="Legacy active",
    )

    tasks = {task.id: task for task in list_project_tasks(manifest, "local")}
    record = load_project_task(manifest, "local", "121")

    assert tasks["TASK-121"].depends_on == ["TASK-120"]
    assert tasks["TASK-121"].ready is True
    assert tasks["TASK-121"].title == "Legacy active"
    assert record.markdown == "# Legacy active\n\n## Objective\n\nLegacy objective\n"


def test_project_task_list_resolves_interruptions_across_active_and_archive(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(
        active_root,
        "parent.yaml",
        "TASK-122",
        state="paused",
        interruption_task_id="TASK-123",
    )
    _write_task(
        archive_root,
        "child.yaml",
        "TASK-123",
        state="completed",
        interruption_source_task_id="TASK-122",
    )

    tasks = {task.id: task for task in list_project_tasks(manifest, "local")}

    assert tasks["TASK-122"].interruption_task_id == "TASK-123"
    assert tasks["TASK-123"].interruption_source_task_id == "TASK-122"


def test_task_reader_rejects_duplicate_ids_and_missing_markdown(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(active_root, "active.yaml", "TASK-120")
    _write_task(archive_root, "archived.yaml", "TASK-120", state="completed")

    with pytest.raises(ServiceError, match="duplicate task id"):
        load_project_task(manifest, "local", "120")

    (archive_root / "archived.md").unlink()
    with pytest.raises(ServiceError, match="failed to load task Markdown"):
        list_project_tasks(manifest, "local")
