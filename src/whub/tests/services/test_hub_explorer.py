"""Hub Explorer filesystem behavior tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.services.errors import NotFoundError
from whub.services.hub_explorer import list_hub_directory, read_hub_file


def test_lists_one_directory_and_excludes_git_through_symlinks(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("z")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide")
    (tmp_path / ".git").mkdir()
    external = tmp_path.parent / f"{tmp_path.name}-external"
    external.mkdir()
    (external / ".git").mkdir()
    (tmp_path / "linked-git").symlink_to(external / ".git", target_is_directory=True)

    entries = list_hub_directory(tmp_path)
    assert ("directory", "docs") in [(entry.type, entry.name) for entry in entries]
    assert ("file", "z.txt") in [(entry.type, entry.name) for entry in entries]
    assert "linked-git" not in [entry.name for entry in entries]
    assert [entry.path for entry in list_hub_directory(tmp_path, "docs")] == [
        "docs/guide.md"
    ]


def test_stops_expanding_a_cyclic_symlink(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "again").symlink_to("..", target_is_directory=True)

    entry = list_hub_directory(tmp_path, "docs")[0]

    assert entry.model_dump() == {
        "name": "again",
        "path": "docs/again",
        "type": "directory",
        "expandable": False,
    }


def test_reads_text_and_rejects_paths_outside_the_logical_root(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("hello")

    assert read_hub_file(tmp_path, "note.txt").model_dump() == {
        "path": "note.txt",
        "content": "hello",
        "state": "text",
    }
    with pytest.raises(NotFoundError, match="hub path not found"):
        list_hub_directory(tmp_path, "../outside")
    with pytest.raises(NotFoundError, match="hub file not found"):
        read_hub_file(tmp_path, ".git/config")
