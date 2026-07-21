"""Project-scoped Task service tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whub.models import Manifest
from whub.services.errors import NotFoundError, ServiceError
from whub.services.task import (
    list_project_tasks,
    load_project_task,
    render_project_task_flow,
    resolve_project_task_root,
)
from whub.tests.helpers import manifest_data


def _write_task(root: Path, task_id: str, title: str) -> None:
    task_root = root / "docs" / "tasks"
    task_root.mkdir(parents=True, exist_ok=True)
    (task_root / f"{task_id.lower()}.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "task": {
                    "id": task_id,
                    "state": "draft",
                    "title": title,
                    "objective": f"Complete {title}",
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
    )


def test_lists_tasks_from_local_remote_and_workspace_hub(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path))
    data = manifest_data()
    local_root = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_root)
    data["projects"].append({"name": "workspace-hub"})
    _write_task(local_root, "TASK-001", "Local")
    _write_task(tmp_path / "projects" / "remote", "TASK-001", "Remote")
    _write_task(tmp_path, "TASK-001", "Workspace")
    loaded_manifest = Manifest.model_validate(data)

    assert list_project_tasks(loaded_manifest, "local")[0].title == "Local"
    assert list_project_tasks(loaded_manifest, "remote")[0].title == "Remote"
    assert list_project_tasks(loaded_manifest, "workspace-hub")[0].title == "Workspace"


def test_distinguishes_missing_tasks_from_unavailable_resource(
    tmp_path: Path,
) -> None:
    data = manifest_data()
    local_root = tmp_path / "local-source"
    local_root.mkdir()
    data["projects"][0]["resource"]["source"] = str(local_root)
    loaded_manifest = Manifest.model_validate(data)

    assert list_project_tasks(loaded_manifest, "local") == ()
    with pytest.raises(
        ServiceError,
        match="project resource is not available: remote",
    ):
        list_project_tasks(loaded_manifest, "remote")
    with pytest.raises(ServiceError, match="project has no resource: no-resource"):
        list_project_tasks(loaded_manifest, "no-resource")


def test_resolves_task_root_and_rejects_non_directory(
    tmp_path: Path,
) -> None:
    data = manifest_data()
    local_root = tmp_path / "local-source"
    local_root.mkdir()
    data["projects"][0]["resource"]["source"] = str(local_root)
    loaded_manifest = Manifest.model_validate(data)

    assert resolve_project_task_root(loaded_manifest, "local") == (
        local_root / "docs/tasks"
    )

    task_path = local_root / "docs/tasks"
    task_path.parent.mkdir()
    task_path.write_text("not a directory")
    with pytest.raises(
        ServiceError,
        match="project task path is not a directory: local",
    ):
        resolve_project_task_root(loaded_manifest, "local")


def test_loads_and_renders_one_project_task(tmp_path: Path) -> None:
    data = manifest_data()
    local_root = tmp_path / "local-source"
    data["projects"][0]["resource"]["source"] = str(local_root)
    _write_task(local_root, "TASK-001", "Local")
    loaded_manifest = Manifest.model_validate(data)

    assert load_project_task(loaded_manifest, "local", "TASK-001").task.title == "Local"
    assert render_project_task_flow(
        loaded_manifest,
        "local",
        "TASK-001",
    ).startswith("flowchart TD")

    with pytest.raises(NotFoundError, match="task not found: local/TASK-999"):
        load_project_task(loaded_manifest, "local", "TASK-999")
