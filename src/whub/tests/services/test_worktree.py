from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from whub.models import Manifest, SymlinkResource, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.worktree import (
    list_worktree_definitions,
    require_worktree_parent,
    save_worktree_definition,
    worktree_definition_path,
)
from whub.tests.helpers import manifest_data


def local_git_manifest() -> Manifest:
    data = manifest_data()
    data["projects"][0]["resource"]["git"] = {"url": "git@example.com:local.git"}
    return Manifest.model_validate(data)


def worktree_definition(
    task_id: str = "TASK-072",
    parent_project: str = "local",
) -> WorktreeDefinition:
    number = task_id.removeprefix("TASK-")
    return WorktreeDefinition(
        task_id=task_id,
        parent_project=parent_project,
        branch=f"tasks/{number}",
        workspace_path=f"projects/worktrees/{parent_project}-{number}",
    )


def test_require_worktree_parent_accepts_local_resource_with_git() -> None:
    resource = require_worktree_parent(local_git_manifest(), "local")
    assert isinstance(resource, SymlinkResource)
    assert resource.git is not None


def test_require_worktree_parent_rejects_local_resource_without_git() -> None:
    with pytest.raises(ServiceError, match="worktree parent has no git declaration: local"):
        require_worktree_parent(Manifest.model_validate(manifest_data()), "local")


def test_require_worktree_parent_rejects_remote_resource_with_git() -> None:
    data = manifest_data()
    data["projects"][1]["resource"]["git"] = {"url": "git@example.com:remote.git"}
    with pytest.raises(ServiceError, match="not a local resource: remote"):
        require_worktree_parent(Manifest.model_validate(data), "remote")


@pytest.mark.parametrize(
    ("project", "message"),
    [
        ("missing", "unknown project: missing"),
        ("no-resource", "project has no resource: no-resource"),
    ],
)
def test_require_worktree_parent_rejects_unusable_project(
    project: str,
    message: str,
) -> None:
    with pytest.raises(ServiceError, match=message):
        require_worktree_parent(local_git_manifest(), project)


def test_save_worktree_definition_creates_canonical_yaml(tmp_path: Path) -> None:
    definition = worktree_definition()

    path = save_worktree_definition(tmp_path, definition)

    assert path == worktree_definition_path(tmp_path, definition)
    assert yaml.safe_load(path.read_text()) == definition.model_dump(mode="json")


def test_save_worktree_definition_rejects_duplicate_task(tmp_path: Path) -> None:
    save_worktree_definition(tmp_path, worktree_definition())

    with pytest.raises(ServiceError, match="duplicate worktree task ID: TASK-072"):
        save_worktree_definition(tmp_path, worktree_definition())


def test_save_worktree_definition_does_not_overwrite_existing_name(
    tmp_path: Path,
) -> None:
    definition = worktree_definition()
    path = worktree_definition_path(tmp_path, definition)
    path.parent.mkdir(parents=True)
    path.write_text("invalid: true\n")

    with pytest.raises(ServiceError, match=f"worktree definition already exists: {path.name}"):
        save_worktree_definition(tmp_path, definition)


def test_save_worktree_definition_serializes_duplicate_task_creations(
    tmp_path: Path,
) -> None:
    definitions = [
        worktree_definition(parent_project="local"),
        worktree_definition(parent_project="other"),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda definition: _save_result(tmp_path, definition),
                definitions,
            )
        )

    assert sum(isinstance(result, Path) for result in results) == 1
    assert sum(isinstance(result, ServiceError) for result in results) == 1
    assert len(list(worktree_definition_path(tmp_path, definitions[0]).parent.glob("*.yaml"))) == 1


def test_list_worktree_definitions_reports_recoverable_inconsistencies(
    tmp_path: Path,
) -> None:
    definition = worktree_definition()
    directory = worktree_definition_path(tmp_path, definition).parent
    directory.mkdir(parents=True)
    (directory / "invalid.yaml").write_text("invalid: true\n")
    (directory / "renamed.yaml").write_text(
        yaml.safe_dump(definition.model_dump(mode="json"), sort_keys=False)
    )

    records = list_worktree_definitions(tmp_path)

    invalid = next(record for record in records if record.path.name == "invalid.yaml")
    renamed = next(record for record in records if record.path.name == "renamed.yaml")
    assert invalid.definition is None
    assert invalid.diagnostics[0].startswith("invalid worktree definition YAML")
    assert renamed.definition == definition
    assert "worktree definition name does not match identity: renamed.yaml" in renamed.diagnostics
    assert "worktree directory is missing: projects/worktrees/local-072" in renamed.diagnostics


def _save_result(workspace_root: Path, definition: WorktreeDefinition) -> Path | ServiceError:
    try:
        return save_worktree_definition(workspace_root, definition)
    except ServiceError as error:
        return error
