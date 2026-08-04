from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
from unittest.mock import call, patch

import pytest
import yaml

from whub.models import Manifest, SymlinkResource, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.worktree import (
    list_worktree_definitions,
    save_worktree_definition,
    worktree_definition_path,
)
from whub.services.worktree.lifecycle import (
    _create_worktree,
    create_project_worktree,
    remove_project_worktree,
)
from whub.services.worktree.pull_request import (
    create_project_pull_request,
    merge_project_pull_request,
)
from whub.services.worktree.resolve import (
    ResolvedProjectWorktree,
    _require_worktree_parent,
    resolve_project_worktree,
    resolve_worktree_parent,
)
from whub.services.worktree.diff import (
    WorktreeDiff,
    list_changed_files,
    read_changed_file_diff,
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
    with (
        patch(
            "whub.services.worktree.check.inspect_worktrees",
            return_value=[inspection],
        ),
        patch("whub.services.worktree.resolve.load_project_task") as load_task,
    ):
        resolved = resolve_project_worktree(
            Manifest.model_validate(data), tmp_path, "local", "TASK-072"
        )

    assert resolved.definition == definition
    assert resolved.parent == source
    assert resolved.destination == tmp_path / definition.workspace_path
    assert resolved.base_branch == "main"
    load_task.assert_called_once_with(
        Manifest.model_validate(data), "local", "TASK-072"
    )


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


def test_list_changed_files_returns_full_tree_without_deleted_files(tmp_path: Path) -> None:
    resolved = ResolvedProjectWorktree(
        definition=worktree_definition(),
        parent=tmp_path / "source",
        destination=tmp_path / "worktree",
        base_branch="main",
    )
    with (
        patch(
            "whub.services.worktree.diff.resolve_project_worktree",
            return_value=resolved,
        ),
        patch(
            "whub.services.worktree.diff.run_git",
            side_effect=[
                subprocess.CompletedProcess(
                    [], 0, stdout="README.md\0new.py\0unchanged.py\0draft.py\0"
                ),
                subprocess.CompletedProcess(
                    [],
                    0,
                    stdout="M\0README.md\0R100\0old.py\0new.py\0D\0deleted.py\0",
                ),
                subprocess.CompletedProcess([], 0, stdout="draft.py\0"),
            ],
        ) as git,
    ):
        files = list_changed_files(
            Manifest.model_validate(manifest_data()), tmp_path, "local", "TASK-072"
        )

    assert len(files) == 4
    assert [item.path for item in files] == [
        "README.md",
        "draft.py",
        "new.py",
        "unchanged.py",
    ]
    assert files[0].path == "README.md"
    assert files[0].status == "M"
    assert files[0].previous_path is None
    assert files[1].status == "A"
    assert files[2].status == "R"
    assert files[2].previous_path == "old.py"
    assert files[3].status == ""
    assert git.call_args_list == [
        call(
            resolved.destination,
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ),
        call(resolved.destination, "diff", "--name-status", "-z", "main"),
        call(
            resolved.destination,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ),
    ]


def test_read_changed_file_diff_rejects_path_outside_worktree(tmp_path: Path) -> None:
    resolved = ResolvedProjectWorktree(
        definition=worktree_definition(),
        parent=tmp_path / "source",
        destination=tmp_path / "worktree",
        base_branch="main",
    )
    with (
        patch(
            "whub.services.worktree.diff.resolve_project_worktree",
            return_value=resolved,
        ),
        patch(
            "whub.services.worktree.diff.run_git",
            return_value=subprocess.CompletedProcess([], 0, stdout="README.md\0"),
        ) as git,
        pytest.raises(ServiceError, match="worktree file not found: pyproject.toml"),
    ):
        read_changed_file_diff(
            Manifest.model_validate(manifest_data()),
            tmp_path,
            "local",
            "TASK-072",
            "pyproject.toml",
        )

    git.assert_called_once_with(
        resolved.destination,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )


def test_read_changed_file_diff_reads_untracked_file(tmp_path: Path) -> None:
    destination = tmp_path / "worktree"
    destination.mkdir()
    (destination / "draft.py").write_text("draft\n")
    resolved = ResolvedProjectWorktree(
        definition=worktree_definition(),
        parent=tmp_path / "source",
        destination=destination,
        base_branch="main",
    )
    with (
        patch(
            "whub.services.worktree.diff.resolve_project_worktree",
            return_value=resolved,
        ),
        patch(
            "whub.services.worktree.diff.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout="draft.py\0"),
                subprocess.CompletedProcess([], 0, stdout="draft.py\0"),
                subprocess.CompletedProcess(
                    [], 1, stdout="@@ -0,0 +1 @@\n+draft\n"
                ),
            ],
        ) as git,
    ):
        diff = read_changed_file_diff(
            Manifest.model_validate(manifest_data()),
            tmp_path,
            "local",
            "TASK-072",
            "draft.py",
        )

    assert diff == WorktreeDiff(
        path="draft.py",
        content="draft\n",
        diff="@@ -0,0 +1 @@\n+draft\n",
        state="text",
    )
    assert git.call_args_list[-1] == call(
        resolved.destination,
        "diff",
        "--no-index",
        "--no-ext-diff",
        "--unified=3",
        "--",
        "/dev/null",
        "draft.py",
    )


def test_read_changed_file_diff_excludes_binary_content(tmp_path: Path) -> None:
    destination = tmp_path / "worktree"
    destination.mkdir()
    (destination / "image.bin").write_bytes(b"\0binary")
    resolved = ResolvedProjectWorktree(
        definition=worktree_definition(),
        parent=tmp_path / "source",
        destination=destination,
        base_branch="main",
    )
    with (
        patch(
            "whub.services.worktree.diff.resolve_project_worktree",
            return_value=resolved,
        ),
        patch(
            "whub.services.worktree.diff.run_git",
            return_value=subprocess.CompletedProcess([], 0, stdout="image.bin\0"),
        ) as git,
    ):
        diff = read_changed_file_diff(
            Manifest.model_validate(manifest_data()),
            tmp_path,
            "local",
            "TASK-072",
            "image.bin",
        )

    assert diff == WorktreeDiff(
        path="image.bin", content=None, diff="", state="binary"
    )
    git.assert_called_once_with(
        destination,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )


def test_read_changed_file_diff_rejects_symlink(tmp_path: Path) -> None:
    destination = tmp_path / "worktree"
    destination.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret\n")
    (destination / "secret-link").symlink_to(outside)
    resolved = ResolvedProjectWorktree(
        definition=worktree_definition(),
        parent=tmp_path / "source",
        destination=destination,
        base_branch="main",
    )
    with (
        patch(
            "whub.services.worktree.diff.resolve_project_worktree",
            return_value=resolved,
        ),
        patch(
            "whub.services.worktree.diff.run_git",
            return_value=subprocess.CompletedProcess([], 0, stdout="secret-link\0"),
        ) as git,
    ):
        diff = read_changed_file_diff(
            Manifest.model_validate(manifest_data()),
            tmp_path,
            "local",
            "TASK-072",
            "secret-link",
        )

    assert diff == WorktreeDiff(
        path="secret-link", content=None, diff="", state="unreadable"
    )
    git.assert_called_once_with(
        destination,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )


def test_read_changed_file_diff_rejects_symlink_replaced_after_lstat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "worktree"
    destination.mkdir()
    inside = destination / "inside.txt"
    inside.write_text("inside\n")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret\n")
    resolved = ResolvedProjectWorktree(
        definition=worktree_definition(),
        parent=tmp_path / "source",
        destination=destination,
        base_branch="main",
    )
    original_lstat = Path.lstat

    def replace_after_lstat(candidate: Path):
        result = original_lstat(candidate)
        if candidate == inside:
            inside.unlink()
            inside.symlink_to(outside)
        return result

    with (
        patch(
            "whub.services.worktree.diff.resolve_project_worktree",
            return_value=resolved,
        ),
        patch(
            "whub.services.worktree.diff.run_git",
            return_value=subprocess.CompletedProcess([], 0, stdout="inside.txt\0"),
        ) as git,
    ):
        monkeypatch.setattr(Path, "lstat", replace_after_lstat)
        diff = read_changed_file_diff(
            Manifest.model_validate(manifest_data()),
            tmp_path,
            "local",
            "TASK-072",
            "inside.txt",
        )

    assert diff == WorktreeDiff(
        path="inside.txt", content=None, diff="", state="unreadable"
    )
    git.assert_called_once_with(
        destination,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
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
        patch("whub.services.worktree.resolve.load_project_task"),
        patch(
            "whub.services.worktree.pull_request.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ) as git,
        patch(
            "whub.services.worktree.pull_request.run_gh",
            return_value=subprocess.CompletedProcess(
                [], 0, stdout="https://example/pr/72\n"
            ),
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
        "whub.services.worktree.lifecycle.run_git",
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
        "whub.services.worktree.lifecycle.run_git",
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
        "whub.services.worktree.lifecycle.run_git",
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
            "whub.services.worktree.lifecycle.load_project_task",
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
            "whub.services.worktree.lifecycle.run_git",
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
            "whub.services.worktree.lifecycle.run_git",
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
        patch("whub.services.worktree.lifecycle.run_git") as run,
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
            "whub.services.worktree.lifecycle.run_git",
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
        patch("whub.services.worktree.resolve.load_project_task"),
        patch(
            "whub.services.worktree.pull_request.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ),
        patch(
            "whub.services.worktree.pull_request.run_gh",
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
        patch("whub.services.worktree.resolve.load_project_task"),
        patch(
            "whub.services.worktree.pull_request.run_git",
            return_value=subprocess.CompletedProcess([], 0, stdout=" M changed.py\n"),
        ),
        patch("whub.services.worktree.pull_request.run_gh") as gh,
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
        patch("whub.services.worktree.resolve.load_project_task"),
        patch(
            "whub.services.worktree.pull_request.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ),
        patch(
            "whub.services.worktree.pull_request.run_gh",
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
        patch("whub.services.worktree.resolve.load_project_task"),
        patch(
            "whub.services.worktree.pull_request.run_git",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0),
            ],
        ),
        patch(
            "whub.services.worktree.pull_request.run_gh",
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


def test_merge_pull_request_removes_worktree_only_after_confirmation(
    tmp_path: Path,
) -> None:
    service_manifest = local_git_manifest()
    definition = worktree_definition()
    resolved = ResolvedProjectWorktree(
        definition,
        tmp_path / "source",
        tmp_path / definition.workspace_path,
        "main",
    )
    with (
        patch(
            "whub.services.worktree.pull_request.resolve_project_worktree",
            return_value=resolved,
        ),
        patch("whub.services.worktree.pull_request._require_clean_worktree"),
        patch(
            "whub.services.worktree.pull_request.run_gh",
            side_effect=[
                subprocess.CompletedProcess(
                    [],
                    0,
                    stdout='[{"url":"https://example/pr/72","headRefOid":"abc"}]',
                ),
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, stdout="MERGED\n"),
            ],
        ),
        patch("whub.services.worktree.pull_request.remove_project_worktree") as remove,
    ):
        merge_project_pull_request(
            service_manifest, tmp_path, "local", "TASK-072", "squash"
        )

    remove.assert_called_once_with(service_manifest, tmp_path, "local", "TASK-072")


def test_merge_pull_request_reports_merge_failure(tmp_path: Path) -> None:
    definition = worktree_definition()
    resolved = ResolvedProjectWorktree(
        definition, tmp_path / "source", tmp_path / definition.workspace_path, "main"
    )
    with (
        patch(
            "whub.services.worktree.pull_request.resolve_project_worktree",
            return_value=resolved,
        ),
        patch("whub.services.worktree.pull_request._require_clean_worktree"),
        patch(
            "whub.services.worktree.pull_request.run_gh",
            side_effect=[
                subprocess.CompletedProcess(
                    [], 0, stdout='[{"url":"https://example/pr/72","headRefOid":"abc"}]'
                ),
                subprocess.CompletedProcess([], 1, stderr="review required"),
            ],
        ),
        patch("whub.services.worktree.pull_request.remove_project_worktree") as remove,
        pytest.raises(ServiceError, match="gh PR merge failed: review required"),
    ):
        merge_project_pull_request(
            local_git_manifest(), tmp_path, "local", "TASK-072", "merge"
        )

    remove.assert_not_called()


def test_merge_pull_request_reports_cleanup_failure_after_merge(tmp_path: Path) -> None:
    definition = worktree_definition()
    resolved = ResolvedProjectWorktree(
        definition, tmp_path / "source", tmp_path / definition.workspace_path, "main"
    )
    with (
        patch(
            "whub.services.worktree.pull_request.resolve_project_worktree",
            return_value=resolved,
        ),
        patch("whub.services.worktree.pull_request._require_clean_worktree"),
        patch(
            "whub.services.worktree.pull_request.run_gh",
            side_effect=[
                subprocess.CompletedProcess(
                    [], 0, stdout='[{"url":"https://example/pr/72","headRefOid":"abc"}]'
                ),
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, stdout="MERGED\n"),
            ],
        ),
        patch(
            "whub.services.worktree.pull_request.remove_project_worktree",
            side_effect=ServiceError("git worktree remove failed: locked"),
        ),
        pytest.raises(
            ServiceError,
            match="pull request merged but cleanup failed: git worktree remove failed: locked",
        ),
    ):
        merge_project_pull_request(
            local_git_manifest(), tmp_path, "local", "TASK-072", "rebase"
        )


def test_merge_pull_request_keeps_worktree_when_not_merged(tmp_path: Path) -> None:
    service_manifest = local_git_manifest()
    definition = worktree_definition()
    resolved = ResolvedProjectWorktree(
        definition,
        tmp_path / "source",
        tmp_path / definition.workspace_path,
        "main",
    )
    with (
        patch(
            "whub.services.worktree.pull_request.resolve_project_worktree",
            return_value=resolved,
        ),
        patch("whub.services.worktree.pull_request._require_clean_worktree"),
        patch(
            "whub.services.worktree.pull_request.run_gh",
            side_effect=[
                subprocess.CompletedProcess(
                    [],
                    0,
                    stdout='[{"url":"https://example/pr/72","headRefOid":"abc"}]',
                ),
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, stdout="OPEN\n"),
            ],
        ),
        patch("whub.services.worktree.pull_request.remove_project_worktree") as remove,
        pytest.raises(ServiceError, match="pull request was not merged"),
    ):
        merge_project_pull_request(
            service_manifest, tmp_path, "local", "TASK-072", "merge"
        )

    remove.assert_not_called()


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ("[]", "open pull request not found: local/TASK-072"),
        ("[{}, {}]", "multiple open pull requests found: local/TASK-072"),
    ],
)
def test_merge_pull_request_requires_one_matching_open_pr(
    tmp_path: Path, output: str, message: str
) -> None:
    definition = worktree_definition()
    resolved = ResolvedProjectWorktree(
        definition, tmp_path / "source", tmp_path / definition.workspace_path, "main"
    )
    with (
        patch(
            "whub.services.worktree.pull_request.resolve_project_worktree",
            return_value=resolved,
        ),
        patch("whub.services.worktree.pull_request._require_clean_worktree"),
        patch(
            "whub.services.worktree.pull_request.run_gh",
            return_value=subprocess.CompletedProcess([], 0, stdout=output),
        ),
        patch("whub.services.worktree.pull_request.remove_project_worktree") as remove,
        pytest.raises(ServiceError, match=message),
    ):
        merge_project_pull_request(
            local_git_manifest(), tmp_path, "local", "TASK-072", "merge"
        )

    remove.assert_not_called()


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
