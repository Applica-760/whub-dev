from pathlib import Path

import pytest

from whub.models import GitInfo
from whub.services.errors import ServiceError
from whub.services.worktree.resolve import (
    resolve_conventional_worktree,
    resolve_worktree,
    worktree_exists,
)
from whub.tests.helpers import manifest


def _manifest_with_git():
    value = manifest()
    project = value.resolve_project("local")
    assert project is not None and project.resource is not None
    project.resource.git = GitInfo(url="git@github.com:Applica-760/whub.git", branch="main")
    return value


def test_resolve_worktree_uses_issue_number_for_names(tmp_path: Path) -> None:
    worktree = resolve_worktree(_manifest_with_git(), tmp_path, "local", 29)

    assert worktree.issue_number == 29
    assert worktree.branch == "issue/29"
    assert worktree.destination == tmp_path / "projects/worktrees/local-29"
    assert worktree.base_branch == "main"


def test_resolve_worktree_requires_a_positive_issue_number(tmp_path: Path) -> None:
    with pytest.raises(ServiceError, match="issue number must be positive"):
        resolve_worktree(_manifest_with_git(), tmp_path, "local", 0)


def test_resolve_conventional_worktree_requires_its_destination(tmp_path: Path) -> None:
    value = _manifest_with_git()
    destination = tmp_path / "projects/worktrees/local-29"
    destination.mkdir(parents=True)

    assert (
        resolve_conventional_worktree(value, tmp_path, "local", 29).destination
        == destination
    )


def test_worktree_exists_requires_a_directory(tmp_path: Path) -> None:
    worktree = resolve_worktree(_manifest_with_git(), tmp_path, "local", 29)
    assert not worktree_exists(worktree)

    assert isinstance(worktree.destination, Path)
    worktree.destination.parent.mkdir(parents=True)
    worktree.destination.touch()
    assert not worktree_exists(worktree)

    worktree.destination.unlink()
    worktree.destination.mkdir()
    assert worktree_exists(worktree)
