from pathlib import Path
import subprocess
from unittest.mock import patch

from whub.models import Manifest, WorktreeDefinition
from whub.services.worktree import save_worktree_definition
from whub.services.worktree.check import inspect_worktrees
from whub.tests.helpers import manifest_data


def _definition(project: str = "local") -> WorktreeDefinition:
    return WorktreeDefinition(
        task_id="TASK-072", parent_project=project, branch="tasks/072"
    )


def _manifest(source: Path) -> Manifest:
    data = manifest_data()
    data["projects"][0]["resource"].update(
        git={"url": "git@example.com:local.git"}, source=str(source)
    )
    data["projects"][1]["resource"]["git"] = {"url": "git@example.com:remote.git"}
    return Manifest.model_validate(data)


def _git_worktree_output(path: Path, branch: str = "tasks/072") -> str:
    return f"worktree {path}\nHEAD deadbeef\nbranch refs/heads/{branch}\n\n"


def test_inspect_worktrees_accepts_matching_local_git_worktree(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    definition = _definition()
    destination = tmp_path / "projects/worktrees/local-072"
    save_worktree_definition(tmp_path, definition)
    with patch(
        "whub.services.worktree.git.run_git",
        return_value=subprocess.CompletedProcess([], 0, stdout=_git_worktree_output(destination)),
    ):
        inspections = inspect_worktrees(_manifest(source), tmp_path)

    assert inspections[0].definition == definition
    assert inspections[0].diagnostics == ()


def test_inspect_worktrees_reports_missing_remote_git_worktree(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    save_worktree_definition(tmp_path, _definition("remote"))
    with patch(
        "whub.services.worktree.git.run_remote_git",
        return_value=subprocess.CompletedProcess([], 0, stdout=""),
    ):
        inspections = inspect_worktrees(_manifest(source), tmp_path)

    assert inspections[0].diagnostics == (
        "git worktree is missing: /srv/worktrees/remote-072",
    )


def test_inspect_worktrees_reports_branch_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    definition = _definition()
    destination = tmp_path / "projects/worktrees/local-072"
    save_worktree_definition(tmp_path, definition)
    with patch(
        "whub.services.worktree.git.run_git",
        return_value=subprocess.CompletedProcess(
            [], 0, stdout=_git_worktree_output(destination, "tasks/999")
        ),
    ):
        inspections = inspect_worktrees(_manifest(source), tmp_path)

    assert inspections[0].diagnostics == (
        "git worktree branch does not match definition: expected tasks/072, found tasks/999",
    )
