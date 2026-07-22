"""Tests for initializing the fixed user Whub context."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from whub.commands.init import init
from whub.core.context import WhubContext


@pytest.fixture()
def invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    context_dir = tmp_path / "init-context"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.setattr(
        "whub.commands.init.current_context",
        lambda: WhubContext(context_dir),
    )
    return context_dir, workspace_root


def invoke_init(workspace_root: Path, *arguments: str):
    return CliRunner().invoke(
        init,
        ["--workspace-root", str(workspace_root), *arguments],
    )


def test_creates_config_in_fixed_context(invocation: tuple[Path, Path]) -> None:
    context_dir, workspace_root = invocation

    result = invoke_init(workspace_root)

    config_path = context_dir / "config.toml"
    assert result.exit_code == 0
    assert "init" in result.output
    assert config_path.read_text() == f'workspace_root = "{workspace_root}"\n'


def test_skips_matching_config(invocation: tuple[Path, Path]) -> None:
    context_dir, workspace_root = invocation
    invoke_init(workspace_root)

    result = invoke_init(workspace_root)

    assert result.exit_code == 0
    assert "skip" in result.output
    assert (context_dir / "config.toml").is_file()


def test_rejects_existing_config_without_force(
    invocation: tuple[Path, Path],
) -> None:
    context_dir, workspace_root = invocation
    context_dir.mkdir()
    config_path = context_dir / "config.toml"
    config_path.write_text('workspace_root = "/legacy"\n')

    result = invoke_init(workspace_root)

    assert result.exit_code != 0
    assert "--force" in result.output
    assert config_path.read_text() == 'workspace_root = "/legacy"\n'


def test_overwrites_existing_config_with_force(
    invocation: tuple[Path, Path],
) -> None:
    context_dir, workspace_root = invocation
    context_dir.mkdir()
    config_path = context_dir / "config.toml"
    config_path.write_text('workspace_root = "/legacy"\n')

    result = invoke_init(workspace_root, "--force")

    assert result.exit_code == 0
    assert "init" in result.output
    assert config_path.read_text() == f'workspace_root = "{workspace_root}"\n'


def test_rejects_context_path_that_is_not_directory(
    invocation: tuple[Path, Path],
) -> None:
    context_dir, workspace_root = invocation
    context_dir.write_text("not a directory")

    result = invoke_init(workspace_root)

    assert result.exit_code != 0
    assert "is not a directory" in result.output
