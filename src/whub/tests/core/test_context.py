"""WhubContext fixed-default and managed-file access tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.core.context import (
    DEFAULT_CONTEXT_DIR,
    PathError,
    WhubContext,
    current_context,
    reset_context,
)


def write_config(context_dir: Path, workspace_root: Path) -> None:
    context_dir.mkdir(parents=True)
    context_dir.joinpath("config.toml").write_text(
        f'workspace_root = "{workspace_root}"\n'
    )


def test_context_uses_directory_directly(tmp_path: Path) -> None:
    context_dir = tmp_path / "subject-context"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    write_config(context_dir, workspace_root)

    context = WhubContext(context_dir)

    assert context.directory == context_dir
    assert context.config_path == context_dir / "config.toml"
    assert context.manifest_path == context_dir / "manifest.yaml"
    assert context.todo_path == context_dir / "todos.yaml"
    assert context.downloads_dir == workspace_root / "downloads"
    assert context.releases_dir == context_dir / "releases"
    assert context.workspace_root == workspace_root


def test_default_context_is_fixed_despite_invocation_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWD", str(tmp_path))
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path / "override-root"))
    monkeypatch.setenv("WHUB_DATA_DIR", str(tmp_path / "override-data"))
    reset_context()

    assert current_context().directory == DEFAULT_CONTEXT_DIR


def test_workspace_root_requires_valid_config(tmp_path: Path) -> None:
    context = WhubContext(tmp_path / "missing")

    with pytest.raises(PathError, match="whub config not found"):
        context.workspace_root


@pytest.mark.parametrize(
    "config",
    [
        "",
        'workspace_root = "relative"\n',
        "workspace_root = [\n",
    ],
)
def test_workspace_root_rejects_invalid_config(tmp_path: Path, config: str) -> None:
    context_dir = tmp_path / "subject-context"
    context_dir.mkdir()
    context_dir.joinpath("config.toml").write_text(config)

    with pytest.raises(PathError, match="invalid whub config"):
        WhubContext(context_dir).workspace_root


def test_workspace_root_must_exist(tmp_path: Path) -> None:
    context_dir = tmp_path / "subject-context"
    write_config(context_dir, tmp_path / "missing-workspace")

    with pytest.raises(PathError, match="workspace root does not exist"):
        WhubContext(context_dir).workspace_root


def test_context_owns_manifest_and_todo_io(tmp_path: Path) -> None:
    context_dir = tmp_path / "subject-context"
    context_dir.mkdir()
    context = WhubContext(context_dir)
    context.manifest_path.write_text("version: '2'\n")

    assert context.read_manifest_text() == "version: '2'\n"
    assert context.read_todo_text() is None

    context.write_todo_text("todos: []\n")

    assert context.read_todo_text() == "todos: []\n"


def test_current_context_is_cached_until_reset() -> None:
    reset_context()
    initial = current_context()

    assert current_context() is initial

    reset_context()

    assert current_context() is not initial
    assert current_context().directory == DEFAULT_CONTEXT_DIR
