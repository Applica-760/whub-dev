"""WhubContext discovery and managed-file access tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.core.context import (
    PathError,
    WhubContext,
    current_context,
    find_context_root,
    invocation_path,
    reset_context,
)


def write_context(root: Path, config: str = "") -> None:
    config_dir = root / ".whub"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(config)


def test_context_uses_whub_directory_directly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    write_context(root, 'data_dir = "/legacy"\n')
    monkeypatch.chdir(root)
    monkeypatch.setenv("PWD", str(root))

    context = WhubContext.discover()

    assert context.root == root
    assert context.config_path == root / ".whub/config.toml"
    assert context.manifest_path == root / ".whub/manifest.yaml"
    assert context.todo_path == root / ".whub/todos.yaml"
    assert context.downloads_dir == root / ".whub/downloads"


def test_legacy_environment_overrides_are_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    write_context(root)
    monkeypatch.chdir(root)
    monkeypatch.setenv("PWD", str(root))
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path / "override-root"))
    monkeypatch.setenv("WHUB_DATA_DIR", str(tmp_path / "override-data"))

    context = WhubContext.discover()

    assert context.root == root
    assert context.manifest_path == root / ".whub/manifest.yaml"


def test_verified_logical_pwd_selects_operation_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = tmp_path / "operation"
    development = tmp_path / "development"
    operation.mkdir()
    development.mkdir()
    write_context(operation)
    logical_checkout = operation / "whub"
    logical_checkout.symlink_to(development, target_is_directory=True)
    monkeypatch.chdir(development)
    monkeypatch.setenv("PWD", str(logical_checkout))

    context = WhubContext.discover()

    assert invocation_path() == logical_checkout
    assert context.root == operation
    assert context.manifest_path == operation / ".whub/manifest.yaml"


def test_context_root_uses_nearest_config(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    inner = outer / "inner"
    nested = inner / "nested"
    nested.mkdir(parents=True)
    write_context(outer)
    write_context(inner)

    assert find_context_root(nested) == inner


def test_context_root_reports_missing_config(tmp_path: Path) -> None:
    with pytest.raises(PathError, match="whub context not found"):
        find_context_root(tmp_path)


def test_unverified_logical_pwd_is_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    physical = tmp_path / "physical"
    unrelated = tmp_path / "unrelated"
    physical.mkdir()
    unrelated.mkdir()
    monkeypatch.chdir(physical)
    monkeypatch.setenv("PWD", str(unrelated))

    assert invocation_path() == physical.resolve()


def test_context_owns_manifest_and_todo_io(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    write_context(root)
    context = WhubContext(root)
    context.manifest_path.write_text("version: '2'\n")

    assert context.read_manifest_text() == "version: '2'\n"
    assert context.read_todo_text() is None

    context.write_todo_text("todos: []\n")

    assert context.read_todo_text() == "todos: []\n"


def test_physical_development_checkout_requires_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    development = tmp_path / "development"
    development.mkdir()
    monkeypatch.chdir(development)
    monkeypatch.setenv("PWD", str(development))

    with pytest.raises(PathError, match="whub context not found"):
        WhubContext.discover()


def test_current_context_is_fixed_until_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    write_context(first)
    write_context(second)
    monkeypatch.chdir(first)
    monkeypatch.setenv("PWD", str(first))

    initial = current_context()
    monkeypatch.chdir(second)
    monkeypatch.setenv("PWD", str(second))

    assert current_context() is initial
    assert current_context().root == first

    reset_context()

    assert current_context().root == second
