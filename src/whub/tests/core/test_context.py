"""WhubContext compatibility and access-boundary tests."""

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
from whub.tests.helpers import write_config


def test_legacy_backend_uses_configured_data_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    data_dir = tmp_path / "data"
    root.mkdir()
    data_dir.mkdir()
    write_config(root, data_dir)
    monkeypatch.setenv("WHUB_ROOT", str(root))
    monkeypatch.delenv("WHUB_DATA_DIR", raising=False)

    context = WhubContext.discover()

    assert context.root == root.resolve()
    assert context.config_path == root.resolve() / ".whub/config.toml"
    assert context.manifest_path == data_dir.resolve() / "manifest.yaml"
    assert context.todo_path == data_dir.resolve() / "todos.yaml"
    assert context.downloads_dir == data_dir.resolve() / "downloads"


def test_data_dir_environment_override_has_legacy_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    configured = tmp_path / "configured"
    override = tmp_path / "override"
    root.mkdir()
    configured.mkdir()
    override.mkdir()
    write_config(root, configured)
    monkeypatch.setenv("WHUB_ROOT", str(root))
    monkeypatch.setenv("WHUB_DATA_DIR", str(override))

    context = WhubContext.discover()

    assert context.manifest_path == override.resolve() / "manifest.yaml"


def test_verified_logical_pwd_selects_operation_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = tmp_path / "operation"
    development = tmp_path / "development"
    data_dir = tmp_path / "data"
    operation.mkdir()
    development.mkdir()
    data_dir.mkdir()
    write_config(operation, data_dir)
    logical_checkout = operation / "whub"
    logical_checkout.symlink_to(development, target_is_directory=True)
    monkeypatch.chdir(development)
    monkeypatch.setenv("PWD", str(logical_checkout))
    monkeypatch.delenv("WHUB_ROOT", raising=False)
    monkeypatch.delenv("WHUB_DATA_DIR", raising=False)

    context = WhubContext.discover()

    assert invocation_path() == logical_checkout
    assert context.root == operation
    assert context.manifest_path == data_dir.resolve() / "manifest.yaml"


def test_context_root_uses_nearest_config(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    inner = outer / "inner"
    nested = inner / "nested"
    nested.mkdir(parents=True)
    for root in (outer, inner):
        config_dir = root / ".whub"
        config_dir.mkdir()
        (config_dir / "config.toml").write_text("")

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


def test_context_owns_manifest_and_todo_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    data_dir = tmp_path / "data"
    root.mkdir()
    data_dir.mkdir()
    write_config(root, data_dir)
    monkeypatch.setenv("WHUB_ROOT", str(root))
    monkeypatch.delenv("WHUB_DATA_DIR", raising=False)
    context = WhubContext.discover()
    context.manifest_path.write_text("version: '2'\n")

    assert context.read_manifest_text() == "version: '2'\n"
    assert context.read_todo_text() is None

    context.write_todo_text("todos: []\n")

    assert context.read_todo_text() == "todos: []\n"


def test_invalid_legacy_config_is_path_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    config_dir = root / ".whub"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text("data_dir = [")
    monkeypatch.setenv("WHUB_ROOT", str(root))
    monkeypatch.delenv("WHUB_DATA_DIR", raising=False)

    with pytest.raises(PathError, match="invalid whub config"):
        WhubContext.discover().manifest_path


def test_missing_legacy_data_dir_config_is_path_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("WHUB_ROOT", str(root))
    monkeypatch.delenv("WHUB_DATA_DIR", raising=False)

    with pytest.raises(PathError, match="data_dir is not configured"):
        WhubContext.discover().manifest_path

    config_dir = root / ".whub"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("other = 'value'\n")

    with pytest.raises(PathError, match="missing data_dir"):
        WhubContext.discover().manifest_path


def test_phase_one_falls_back_to_package_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocation = tmp_path / "invocation"
    package = tmp_path / "package"
    invocation.mkdir()
    package.mkdir()
    monkeypatch.chdir(invocation)
    monkeypatch.setenv("PWD", str(invocation))
    monkeypatch.delenv("WHUB_ROOT", raising=False)
    monkeypatch.setattr("whub.core.context._package_workspace_root", lambda: package)

    assert WhubContext.discover().root == package


def test_current_context_is_fixed_until_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.setenv("WHUB_ROOT", str(first))

    initial = current_context()
    monkeypatch.setenv("WHUB_ROOT", str(second))

    assert current_context() is initial
    assert current_context().root == first.resolve()

    reset_context()

    assert current_context().root == second.resolve()
