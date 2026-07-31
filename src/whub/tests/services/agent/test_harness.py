from pathlib import Path, PurePosixPath
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from whub.models.agent.auth import (
    RegisteredProjectVariable,
    RegisteredTaskWorktreeVariable,
)
from whub.services.agent.adapters.codex import CodexRenderPlan
from whub.services.agent.harness import (
    _PreparedHarness,
    _materialize,
    _resolve_variables,
    _start_tmux_session,
    open_harness,
)
from whub.services.errors import ServiceError


def _plan(content: str = 'sandbox_mode = "workspace-write"\n') -> CodexRenderPlan:
    return CodexRenderPlan({PurePosixPath(".codex/config.toml"): content})


def test_materialize_creates_and_reuses_matching_codex_config(tmp_path: Path) -> None:
    created = _materialize(tmp_path, _plan().files)

    assert created == (tmp_path / ".codex/config.toml",)
    assert created[0].read_text() == 'sandbox_mode = "workspace-write"\n'
    assert _materialize(tmp_path, _plan().files) == created


def test_materialize_rejects_different_existing_codex_config(tmp_path: Path) -> None:
    _materialize(tmp_path, _plan('sandbox_mode = "read-only"\n').files)

    with pytest.raises(ServiceError, match="generated config already exists"):
        _materialize(tmp_path, _plan().files)


def test_materialize_rejects_symlinked_config_directory(tmp_path: Path) -> None:
    target = tmp_path / "outside"
    target.mkdir()
    (tmp_path / ".codex").symlink_to(target, target_is_directory=True)

    with pytest.raises(ServiceError, match="generated config parent is a symlink"):
        _materialize(tmp_path, _plan().files)


def test_resolve_variables_uses_registered_project_and_worktree() -> None:
    values = _resolve_variables(
        {
            "project": RegisteredProjectVariable(source="registered_project"),
            "current_worktree": RegisteredTaskWorktreeVariable(
                source="registered_task_worktree", fields=["project", "task", "path"]
            ),
        },
        "whub-dev",
        "TASK-095",
        Path("/workspace/projects/worktrees/whub-dev-095"),
    )

    assert values == {
        "project": "whub-dev",
        "current_worktree.project": "whub-dev",
        "current_worktree.task": "TASK-095",
        "current_worktree.path": "/workspace/projects/worktrees/whub-dev-095",
    }


def test_start_tmux_session_creates_codex_from_hub_root(tmp_path: Path) -> None:
    harness = _PreparedHarness("whub-dev", "TASK-095", tmp_path / "worktree", ())
    with patch(
        "whub.services.agent.harness.subprocess.run",
        side_effect=[
            CompletedProcess([], 1, "", "missing"),
            CompletedProcess([], 0, "", ""),
        ],
    ) as run:
        session = _start_tmux_session(harness, tmp_path)

    assert session.name == "whub-whub-dev-TASK-095"
    assert session.attach_command == (
        "tmux",
        "attach-session",
        "-t",
        "=whub-whub-dev-TASK-095",
    )
    assert run.call_args_list[1].args[0] == [
        "tmux",
        "new-session",
        "-d",
        "-s",
        "whub-whub-dev-TASK-095",
        "-c",
        str(tmp_path),
        f"cd {tmp_path / 'worktree'} && exec $SHELL -l",
    ]


def test_start_stops_before_tmux_when_worktree_validation_fails(tmp_path: Path) -> None:
    with (
        patch(
            "whub.services.agent.harness.resolve_project_worktree",
            side_effect=ServiceError(
                "worktree definition not found: whub-dev/TASK-095"
            ),
        ),
        patch("whub.services.agent.harness.subprocess.run") as run,
        pytest.raises(ServiceError, match="worktree definition not found"),
    ):
        open_harness(None, tmp_path, "whub-dev", "TASK-095", None, (), None)

    run.assert_not_called()
