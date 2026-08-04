"""Task service behavior tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.core.context import WhubContext
from whub.models import Manifest
from whub.services.manifest import resolve_manifest
from whub.services.task import list_project_tasks, load_project_task
from whub.tests.helpers import manifest_data


_ROOT = Path(__file__).parents[4]
_TASK_FIXTURE = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


@pytest.fixture
def task_storage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Manifest, Path, Path]:
    hub_root = tmp_path / "workspace-hub"
    project_root = tmp_path / "project"
    hub_root.mkdir()
    project_root.mkdir()
    context_dir = tmp_path / "task-context"
    context_dir.mkdir()
    context_dir.joinpath("config.toml").write_text(
        f'workspace_root = "{hub_root}"\n'
    )
    data = manifest_data()
    data["projects"][0]["resource"]["source"] = str(project_root)
    monkeypatch.setattr(
        "whub.services.task.current_context", lambda: WhubContext(context_dir)
    )
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


def test_list_project_tasks_includes_active_and_archived_tasks(
    task_storage: tuple[Manifest, Path, Path],
) -> None:
    manifest, active_root, archive_root = task_storage
    _write_task(active_root, "active.yaml", "TASK-001")
    _write_task(archive_root, "archived.yaml", "TASK-002")

    tasks = list_project_tasks(manifest, "local")

    assert [task.id for task in tasks] == ["TASK-001", "TASK-002"]


def test_load_project_task_falls_back_to_archive(
    task_storage: tuple[Manifest, Path, Path],
) -> None:
    manifest, _, archive_root = task_storage
    _write_task(archive_root, "archived.yaml", "TASK-002")

    task = load_project_task(manifest, "local", "002")

    assert task.task.id == "TASK-002"
