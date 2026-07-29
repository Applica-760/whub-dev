from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
from unittest.mock import call, patch

import pytest
import yaml

from whub.models import Manifest, SymlinkResource, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.worktree import (
    create_project_pull_request,
    create_project_worktree,
    list_worktree_definitions,
    remove_project_worktree,
    resolve_project_worktree,
    resolve_worktree_parent,
    save_worktree_definition,
    worktree_definition_path,
)
from whub.services.worktree.operation import _create_worktree, _require_worktree_parent
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
    resource = _require_worktree_parent(local_git_manifest(), "local")
    assert isinstance(resource, SymlinkResource)
    assert resource.git is not None


def test_require_worktree_parent_rejects_local_resource_without_git() -> None:
    with pytest.raises(
        ServiceError, match="worktree parent has no git declaration: local"
    ):
        _require_worktree_parent(Manifest.model_validate(manifest_data()), "local")


def test_require_worktree_parent_rejects_remote_resource_with_git() -> None:
    data = manifest_data()
    data["projects"][1]["resource"]["git"] = {"url": "git@example.com:remote.git"}
    with pytest.raises(
        ServiceError,
        match="worktree for remote resource is not implemented: remote",
    ):
        _require_worktree_parent(Manifest.model_validate(data), "remote")


def test_resolve_worktree_parent_uses_definition_parent_project(tmp_path: Path) -> None:
    data = manifest_data()
    source = tmp_path / "source"
    source.mkdir()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )

    parent = resolve_worktree_parent(
        Manifest.model_validate(data),
        worktree_definition(),
    )

    assert parent == source


def test_resolve_worktree_parent_rejects_remote_resource_as_unimplemented() -> None:
    data = manifest_data()
    data["projects"][1]["resource"]["git"] = {"url": "git@example.com:remote.git"}

    with pytest.raises(
        ServiceError,
        match="worktree for remote resource is not implemented: remote",
    ):
        resolve_worktree_parent(
            Manifest.model_validate(data),
            worktree_definition(parent_project="remote"),
        )


def test_resolve_project_worktree_returns_pr_lifecycle_inputs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git", "branch": "main"},
        source=str(source),
    )
    definition = worktree_definition()
    inspection = _inspection(tmp_path / "local-072.yaml", definition)
    task = object()
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.operation.load_project_task", return_value=task),
    ):
        resolved = resolve_project_worktree(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert resolved.definition == definition
    assert resolved.parent == source
    assert resolved.destination == tmp_path / definition.workspace_path
    assert resolved.task is task
    assert resolved.base_branch == "main"


def test_resolve_project_worktree_requires_git_base_branch(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )
    definition = worktree_definition()
    inspection = _inspection(tmp_path / "local-072.yaml", definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        pytest.raises(
            ServiceError,
            match="worktree parent has no git branch declaration: local",
        ),
    ):
        resolve_project_worktree(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )


def test_create_pull_request_returns_existing_open_pr(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git", "branch": "main"},
        source=str(source),
    )
    definition = worktree_definition()
    inspection = _inspection(tmp_path / "local-072.yaml", definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.operation.load_project_task"),
        patch(
            "whub.services.worktree.operation.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ) as git,
        patch(
            "whub.services.worktree.operation.run_gh",
            return_value=subprocess.CompletedProcess([], 0, stdout="https://example/pr/72\n"),
        ) as gh,
    ):
        url = create_project_pull_request(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert url == "https://example/pr/72"
    assert git.call_args_list == [
        call(
            tmp_path / definition.workspace_path,
            "status",
            "--porcelain",
            "--untracked-files=all",
        ),
        call(
            tmp_path / definition.workspace_path,
            "push",
            "--set-upstream",
            "origin",
            "tasks/072",
        ),
    ]
    gh.assert_called_once_with(
        tmp_path / definition.workspace_path,
        "pr",
        "list",
        "--head",
        "tasks/072",
        "--base",
        "main",
        "--state",
        "open",
        "--json",
        "url",
        "--jq",
        ".[0].url",
    )


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
        _require_worktree_parent(local_git_manifest(), project)


def test_save_worktree_definition_creates_canonical_yaml(tmp_path: Path) -> None:
    definition = worktree_definition()

    path = save_worktree_definition(tmp_path, definition)

    assert path == worktree_definition_path(tmp_path, definition)
    assert yaml.safe_load(path.read_text()) == definition.model_dump(mode="json")


def test_create_worktree_saves_definition_then_adds_existing_branch(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )
    definition = worktree_definition()
    with patch(
        "whub.services.worktree.operation.run_git",
        side_effect=[
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 0),
        ],
    ) as run:
        path = _create_worktree(Manifest.model_validate(data), tmp_path, definition)

    assert path == tmp_path / definition.workspace_path
    assert worktree_definition_path(tmp_path, definition).is_file()
    assert run.call_args_list == [
        call(
            source,
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/tasks/072",
        ),
        call(
            source,
            "worktree",
            "add",
            str(path),
            "tasks/072",
        ),
    ]


def test_create_worktree_creates_missing_branch(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )
    definition = worktree_definition()
    with patch(
        "whub.services.worktree.operation.run_git",
        side_effect=[
            subprocess.CompletedProcess([], 1),
            subprocess.CompletedProcess([], 0),
        ],
    ) as run:
        _create_worktree(Manifest.model_validate(data), tmp_path, definition)

    assert run.call_args_list[1] == call(
        source,
        "worktree",
        "add",
        "-b",
        "tasks/072",
        str(tmp_path / definition.workspace_path),
    )


def test_create_worktree_keeps_definition_when_git_add_fails(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )
    definition = worktree_definition()
    with patch(
        "whub.services.worktree.operation.run_git",
        side_effect=[
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 1, stderr="git add failed"),
        ],
    ):
        with pytest.raises(
            ServiceError, match="git worktree add failed: git add failed"
        ):
            _create_worktree(Manifest.model_validate(data), tmp_path, definition)

    assert worktree_definition_path(tmp_path, definition).is_file()


def test_create_project_worktree_rejects_missing_project_task(tmp_path: Path) -> None:
    with (
        patch(
            "whub.services.worktree.operation.load_project_task",
            side_effect=ServiceError("task not found: local/TASK-072"),
        ),
        pytest.raises(ServiceError, match="task not found: local/TASK-072"),
    ):
        create_project_worktree(local_git_manifest(), tmp_path, "local", "TASK-072")

    assert list_worktree_definitions(tmp_path) == []


def test_remove_worktree_removes_clean_git_worktree_then_definition(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )
    definition = worktree_definition()
    destination = tmp_path / definition.workspace_path
    destination.mkdir(parents=True)
    definition_path = save_worktree_definition(tmp_path, definition)
    inspection = _inspection(definition_path, definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch(
            "whub.services.worktree.operation.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ) as run,
    ):
        remove_project_worktree(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert not definition_path.exists()
    assert run.call_args_list == [
        call(destination, "status", "--porcelain", "--untracked-files=all"),
        call(source, "worktree", "remove", str(destination)),
    ]


@pytest.mark.parametrize("status_output", [" M changed.py\n", "?? untracked.py\n"])
def test_remove_worktree_rejects_uncommitted_changes(
    tmp_path: Path,
    status_output: str,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )
    definition = worktree_definition()
    destination = tmp_path / definition.workspace_path
    destination.mkdir(parents=True)
    definition_path = save_worktree_definition(tmp_path, definition)
    inspection = _inspection(definition_path, definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch(
            "whub.services.worktree.operation.run_git",
            return_value=subprocess.CompletedProcess([], 0, stdout=status_output),
        ) as run,
        pytest.raises(
            ServiceError,
            match="worktree has uncommitted changes: projects/worktrees/local-072",
        ),
    ):
        remove_project_worktree(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert definition_path.exists()
    run.assert_called_once_with(
        destination, "status", "--porcelain", "--untracked-files=all"
    )


def test_remove_worktree_rejects_inconsistent_definition(tmp_path: Path) -> None:
    definition = worktree_definition()
    definition_path = save_worktree_definition(tmp_path, definition)
    inspection = _inspection(
        definition_path,
        definition,
        diagnostics=("git worktree is missing: projects/worktrees/local-072",),
    )
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.operation.run_git") as run,
        pytest.raises(
            ServiceError,
            match="cannot remove inconsistent worktree: git worktree is missing",
        ),
    ):
        remove_project_worktree(local_git_manifest(), tmp_path, "local", "TASK-072")

    assert definition_path.exists()
    run.assert_not_called()


def test_remove_worktree_keeps_definition_when_yaml_removal_fails(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"},
        source=str(source),
    )
    definition = worktree_definition()
    destination = tmp_path / definition.workspace_path
    destination.mkdir(parents=True)
    definition_path = save_worktree_definition(tmp_path, definition)
    inspection = _inspection(definition_path, definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch(
            "whub.services.worktree.operation.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ),
        patch.object(Path, "unlink", side_effect=OSError("permission denied")),
        pytest.raises(ServiceError, match="failed to remove worktree definition"),
    ):
        remove_project_worktree(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert definition_path.exists()


def test_save_worktree_definition_rejects_duplicate_task(tmp_path: Path) -> None:
    save_worktree_definition(tmp_path, worktree_definition())

    with pytest.raises(ServiceError, match="duplicate worktree task: local/TASK-072"):
        save_worktree_definition(tmp_path, worktree_definition())


def test_save_worktree_definition_does_not_overwrite_existing_name(
    tmp_path: Path,
) -> None:
    definition = worktree_definition()
    path = worktree_definition_path(tmp_path, definition)
    path.parent.mkdir(parents=True)
    path.write_text("invalid: true\n")

    with pytest.raises(
        ServiceError, match=f"worktree definition already exists: {path.name}"
    ):
        save_worktree_definition(tmp_path, definition)


def test_save_worktree_definition_allows_same_task_id_for_different_projects(
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

    assert all(isinstance(result, Path) for result in results)
    assert (
        len(
            list(
                worktree_definition_path(tmp_path, definitions[0]).parent.glob("*.yaml")
            )
        )
        == 2
    )


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
    assert (
        "worktree definition name does not match identity: renamed.yaml"
        in renamed.diagnostics
    )
    assert (
        "worktree directory is missing: projects/worktrees/local-072"
        in renamed.diagnostics
    )


def test_create_pull_request_creates_when_no_open_pr_exists(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git", "branch": "main"},
        source=str(source),
    )
    definition = worktree_definition()
    inspection = _inspection(tmp_path / "local-072.yaml", definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.operation.load_project_task"),
        patch(
            "whub.services.worktree.operation.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ),
        patch(
            "whub.services.worktree.operation.run_gh",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0, stdout="https://example/pr/72\n"),
            ],
        ) as gh,
    ):
        url = create_project_pull_request(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert url == "https://example/pr/72"
    assert gh.call_args_list[-1] == call(
        tmp_path / definition.workspace_path,
        "pr",
        "create",
        "--base",
        "main",
        "--head",
        "tasks/072",
        "--title",
        "TASK-072",
        "--body",
        "",
    )


def test_create_pull_request_rejects_uncommitted_changes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git", "branch": "main"},
        source=str(source),
    )
    definition = worktree_definition()
    inspection = _inspection(tmp_path / "local-072.yaml", definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.operation.load_project_task"),
        patch(
            "whub.services.worktree.operation.run_git",
            return_value=subprocess.CompletedProcess([], 0, stdout=" M changed.py\n"),
        ),
        patch("whub.services.worktree.operation.run_gh") as gh,
        pytest.raises(ServiceError, match="worktree has uncommitted changes"),
    ):
        create_project_pull_request(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    gh.assert_not_called()


def test_create_pull_request_reports_gh_lookup_failure(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git", "branch": "main"},
        source=str(source),
    )
    definition = worktree_definition()
    inspection = _inspection(tmp_path / "local-072.yaml", definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.operation.load_project_task"),
        patch(
            "whub.services.worktree.operation.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ),
        patch(
            "whub.services.worktree.operation.run_gh",
            return_value=subprocess.CompletedProcess([], 1, stderr="not logged in"),
        ) as gh,
        pytest.raises(ServiceError, match="gh PR lookup failed: not logged in"),
    ):
        create_project_pull_request(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    gh.assert_called_once()


def test_create_pull_request_reports_gh_create_failure(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git", "branch": "main"},
        source=str(source),
    )
    definition = worktree_definition()
    inspection = _inspection(tmp_path / "local-072.yaml", definition)
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.operation.load_project_task"),
        patch(
            "whub.services.worktree.operation.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ),
        patch(
            "whub.services.worktree.operation.run_gh",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 1, stderr="PR creation rejected"),
            ],
        ) as gh,
        pytest.raises(
            ServiceError,
            match="gh PR create failed: PR creation rejected",
        ),
    ):
        create_project_pull_request(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert gh.call_count == 2


def _save_result(
    workspace_root: Path, definition: WorktreeDefinition
) -> Path | ServiceError:
    try:
        return save_worktree_definition(workspace_root, definition)
    except ServiceError as error:
        return error


def _inspection(
    path: Path,
    definition: WorktreeDefinition,
    diagnostics: tuple[str, ...] = (),
):
    from whub.models import WorktreeDefinitionRecord, WorktreeInspection

    return WorktreeInspection(
        WorktreeDefinitionRecord(path, definition),
        diagnostics,
    )
