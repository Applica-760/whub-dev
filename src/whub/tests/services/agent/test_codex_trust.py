from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from whub.services.agent.codex.trust import cleanup, prepare
from whub.services.errors import ServiceError


def _paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    workspace = tmp_path / "workspace"
    worktree = workspace / "projects/worktrees/whub-dev-104"
    codex_home = tmp_path / "home/.codex"
    worktree.mkdir(parents=True)
    return workspace, worktree, codex_home


def test_prepare_and_cleanup_manage_only_owned_worktree_trust(tmp_path: Path) -> None:
    workspace, worktree, codex_home = _paths(tmp_path)

    prepare(workspace, "whub-dev", "TASK-104", worktree, codex_home=codex_home)

    config_path = codex_home / "config.toml"
    config = tomllib.loads(config_path.read_text())
    assert config["projects"][str(worktree)]["trust_level"] == "trusted"

    cleanup(workspace, "whub-dev", "TASK-104", worktree)

    assert not config_path.exists()


def test_prepare_preserves_existing_trusted_project(tmp_path: Path) -> None:
    workspace, worktree, codex_home = _paths(tmp_path)
    config_path = codex_home / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f'[projects."{worktree}"]\ntrust_level = "trusted"\n', encoding="utf-8"
    )

    prepare(workspace, "whub-dev", "TASK-104", worktree, codex_home=codex_home)
    cleanup(workspace, "whub-dev", "TASK-104", worktree)

    assert config_path.read_text() == (
        f'[projects."{worktree}"]\ntrust_level = "trusted"\n'
    )


def test_prepare_refuses_to_override_existing_project_trust(tmp_path: Path) -> None:
    workspace, worktree, codex_home = _paths(tmp_path)
    config_path = codex_home / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        f'[projects."{worktree}"]\ntrust_level = "untrusted"\n', encoding="utf-8"
    )

    with pytest.raises(ServiceError, match="Codex project trust already exists"):
        prepare(workspace, "whub-dev", "TASK-104", worktree, codex_home=codex_home)


def test_cleanup_preserves_modified_owned_trust_entry(tmp_path: Path) -> None:
    workspace, worktree, codex_home = _paths(tmp_path)
    prepare(workspace, "whub-dev", "TASK-104", worktree, codex_home=codex_home)
    config_path = codex_home / "config.toml"
    config_path.write_text(config_path.read_text().replace('"trusted"', '"untrusted"'))

    with pytest.raises(ServiceError, match="whub-owned Codex trust entry was modified"):
        cleanup(workspace, "whub-dev", "TASK-104", worktree)

    assert config_path.exists()
