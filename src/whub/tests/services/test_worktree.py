from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from whub.models import Manifest, WorktreeDefinition
from whub.services.errors import ServiceError
from whub.services.worktree.check import inspect_worktrees
from whub.services.worktree.lifecycle import _create_worktree, remove_project_worktree
from whub.services.worktree.pull_request import create_project_pull_request
from whub.services.worktree.resolve import _resolve_location, resolve_project_worktree
from whub.tests.helpers import manifest_data


def _manifest(tmp_path: Path) -> Manifest:
    data = manifest_data()
    data["projects"][0]["resource"].update(
        source=str(tmp_path / "source"), git={"url": "git@example.com:local.git", "branch": "main"}
    )
    data["projects"][1]["resource"]["git"] = {
        "url": "git@example.com:remote.git", "branch": "main"
    }
    return Manifest.model_validate(data)


def _definition(project: str = "local") -> WorktreeDefinition:
    return WorktreeDefinition(task_id="TASK-072", parent_project=project, branch="tasks/072")


def _inspection(definition: WorktreeDefinition):
    from whub.models import WorktreeDefinitionRecord, WorktreeInspection

    return WorktreeInspection(WorktreeDefinitionRecord(Path("definition.yaml"), definition), ())


def test_resolve_location_uses_resource_specific_roots(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    local_parent, local_destination, local_host = _resolve_location(manifest, tmp_path, _definition())
    remote_parent, remote_destination, remote_host = _resolve_location(
        manifest, tmp_path, _definition("remote")
    )

    assert local_parent == tmp_path / "source"
    assert local_destination == tmp_path / "projects/worktrees/local-072"
    assert local_host is None
    assert remote_parent == "/srv/remote"
    assert remote_destination == "/srv/worktrees/remote-072"
    assert remote_host == manifest.hosts["home"]


@pytest.mark.parametrize("project", ["local", "remote"])
def test_create_dispatches_git_to_resolved_resource(tmp_path: Path, project: str) -> None:
    manifest = _manifest(tmp_path)
    definition = _definition(project)
    with patch(
        "whub.services.worktree.lifecycle.run_worktree_git",
        side_effect=[subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)],
    ) as git:
        destination = _create_worktree(manifest, tmp_path, definition)

    host = None if project == "local" else manifest.hosts["home"]
    assert git.call_args_list[0].args[:2] == (
        host,
        tmp_path / "source" if project == "local" else "/srv/remote",
    )
    assert destination == (
        tmp_path / "projects/worktrees/local-072" if project == "local" else "/srv/worktrees/remote-072"
    )


def test_create_keeps_definition_when_git_add_fails(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    with (
        patch(
            "whub.services.worktree.lifecycle.run_worktree_git",
            side_effect=[subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1, stderr="failed")],
        ),
        pytest.raises(ServiceError, match="git worktree add failed: failed"),
    ):
        _create_worktree(manifest, tmp_path, _definition())

    assert (tmp_path / "projects/worktrees/local-072.yaml").is_file()


def test_remove_rejects_uncommitted_remote_worktree(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    definition = _definition("remote")
    with (
        patch("whub.services.worktree.check.inspect_worktrees", return_value=[_inspection(definition)]),
        patch(
            "whub.services.worktree.lifecycle.run_worktree_git",
            return_value=subprocess.CompletedProcess([], 0, stdout=" M changed.py\n"),
        ),
        pytest.raises(ServiceError, match="worktree has uncommitted changes: /srv/worktrees/remote-072"),
    ):
        remove_project_worktree(manifest, tmp_path, "remote", "TASK-072")


def test_resolve_project_worktree_accepts_remote_registration(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    definition = _definition("remote")
    with (
        patch("whub.services.worktree.check.inspect_worktrees", return_value=[_inspection(definition)]),
        patch("whub.services.worktree.resolve.load_project_task"),
    ):
        resolved = resolve_project_worktree(manifest, tmp_path, "remote", "TASK-072")

    assert resolved.is_remote
    assert resolved.destination == "/srv/worktrees/remote-072"


def test_remote_pull_request_uses_remote_git_and_gh(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    definition = _definition("remote")
    with (
        patch("whub.services.worktree.check.inspect_worktrees", return_value=[_inspection(definition)]),
        patch("whub.services.worktree.resolve.load_project_task"),
        patch(
            "whub.services.worktree.pull_request.run_worktree_git",
            side_effect=[subprocess.CompletedProcess([], 0, stdout=""), subprocess.CompletedProcess([], 0)],
        ) as git,
        patch(
            "whub.services.worktree.pull_request.run_worktree_gh",
            return_value=subprocess.CompletedProcess([], 0, stdout="https://example/pr/72\n"),
        ) as gh,
    ):
        assert create_project_pull_request(manifest, tmp_path, "remote", "TASK-072") == "https://example/pr/72"

    assert git.call_args_list[0].args[:2] == (manifest.hosts["home"], "/srv/worktrees/remote-072")
    assert gh.call_args.args[:2] == (manifest.hosts["home"], "/srv/worktrees/remote-072")


def test_check_reports_remote_worktree_missing(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    definition = _definition("remote")
    from whub.services.worktree.definition import save_worktree_definition

    save_worktree_definition(tmp_path, definition)
    with patch(
        "whub.services.worktree.git.run_remote_git",
        return_value=subprocess.CompletedProcess([], 0, stdout=""),
    ):
        inspection = inspect_worktrees(manifest, tmp_path)[0]

    assert inspection.diagnostics == ("git worktree is missing: /srv/worktrees/remote-072",)
