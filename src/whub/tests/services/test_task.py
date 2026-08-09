"""Task service behavior tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whub.models import Manifest
from whub.services.errors import ServiceError
from whub.services.manifest import ResolvedManifest, resolve_manifest
from whub.services.task.task import list_project_tasks, load_project_task
from whub.tests.helpers import manifest_data


_ROOT = Path(__file__).parents[4]
_TASK_FIXTURE = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


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
        hub_root / "wflow/tasks/local",
        project_root / "docs/tasks/done",
    )


def _write_task(root: Path, filename: str, task_id: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath(filename).write_text(
        _TASK_FIXTURE.read_text().replace("TASK-001", task_id)
    )


def _write_dependent_draft(
    root: Path, filename: str, task_id: str, dependency: str
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(_TASK_FIXTURE.read_text())
    data["task"].update(id=task_id, state="draft", depends_on=[dependency])
    data["approvals"] = []
    data["acceptance_results"] = []
    data["change_requests"] = []
    data["result"] = None
    for phase in data["plan"]["phases"]:
        phase["log"] = []
        for step in phase["steps"]:
            step["state"] = "pending"
    root.joinpath(filename).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    )


def test_list_project_tasks_includes_active_and_archived_tasks(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(active_root, "active.yaml", "TASK-001")
    _write_task(archive_root, "archived.yaml", "TASK-002")

    tasks = list_project_tasks(manifest, "local")

    assert [task.id for task in tasks] == ["TASK-001", "TASK-002"]


def test_load_project_task_falls_back_to_archive(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, _, archive_root = task_storage
    _write_task(archive_root, "archived.yaml", "TASK-002")

    task = load_project_task(manifest, "local", "002")

    assert task.task.id == "TASK-002"


def test_project_task_list_derives_dependencies_across_active_and_archive(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_dependent_draft(active_root, "dependent.yaml", "TASK-122", "TASK-120")
    _write_task(archive_root, "completed.yaml", "TASK-120")

    tasks = {task.id: task for task in list_project_tasks(manifest, "local")}

    assert tasks["TASK-122"].ready is True
    assert tasks["TASK-122"].blocked_by == []


def test_load_project_task_rejects_duplicate_ids_across_storage_roots(
    task_storage: tuple[ResolvedManifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(active_root, "active.yaml", "TASK-120")
    _write_task(archive_root, "archived.yaml", "TASK-120")

    with pytest.raises(ServiceError, match="task ID is ambiguous: TASK-120"):
        load_project_task(manifest, "local", "120")
