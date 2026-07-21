"""AppleDouble path helper tests."""

from pathlib import Path

from whub.utils.apple_double import is_apple_double


def test_identifies_apple_double_by_filename() -> None:
    assert is_apple_double(Path("docs/tasks/._task.yaml"))
    assert not is_apple_double(Path("docs/tasks/task.yaml"))
