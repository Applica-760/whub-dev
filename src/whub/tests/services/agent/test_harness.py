from pathlib import Path, PurePosixPath
from subprocess import CompletedProcess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from whub.models.agent.auth import (
    RegisteredProjectVariable,
    RegisteredTaskWorktreeVariable,
)
from whub.services.agent.adapters.codex import CodexRenderPlan
from whub.services.agent.harness import (
    _PreparedHarness,
    _resolve_variables,
    _start_tmux_session,
    close_harness,
    open_harness,
)
from whub.services.errors import ServiceError
from whub.services.agent.state import cleanup, prepare, state_path


def _plan(content: str = 'sandbox_mode = "workspace-write"\n') -> CodexRenderPlan:
    return CodexRenderPlan({PurePosixPath(".codex/config.toml"): content})


def test_state_creates_and_cleans_owned_config(tmp_path: Path) -> None:
    prepare(tmp_path, "whub-dev", "TASK-095", tmp_path, _plan().files)

    path = tmp_path / ".codex/config.toml"
    assert path.read_text() == 'sandbox_mode = "workspace-write"\n'
    assert state_path(tmp_path, "whub-dev", "TASK-095").exists()
    cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)
    assert not path.exists()
    assert not (tmp_path / ".codex").exists()


def test_state_rejects_different_existing_codex_config(tmp_path: Path) -> None:
    prepare(
        tmp_path,
        "whub-dev",
        "TASK-095",
        tmp_path,
        _plan('sandbox_mode = "read-only"\n').files,
    )

    with pytest.raises(ServiceError, match="generated config already exists"):
        prepare(tmp_path, "whub-dev", "TASK-095", tmp_path, _plan().files)


def test_state_does_not_claim_matching_existing_json_config(tmp_path: Path) -> None:
    path = tmp_path / ".mcp.json"
    path.write_text('{"mcpServers": {"codegraph": {"type": "stdio"}}}\n')

    prepare(
        tmp_path,
        "whub-dev",
        "TASK-095",
        tmp_path,
        {
            PurePosixPath(".mcp.json"): (
                '{\n  "mcpServers": {\n    "codegraph": {\n      "type": "stdio"\n    }\n  }\n}\n'
            )
        },
    )

    assert path.exists()
    assert not state_path(tmp_path, "whub-dev", "TASK-095").exists()


def test_state_rejects_symlinked_config_directory(tmp_path: Path) -> None:
    target = tmp_path / "outside"
    target.mkdir()
    (tmp_path / ".codex").symlink_to(target, target_is_directory=True)

    with pytest.raises(ServiceError, match="generated config path is a symlink"):
        prepare(tmp_path, "whub-dev", "TASK-095", tmp_path, _plan().files)


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
    harness = _PreparedHarness("whub-dev", "TASK-095", tmp_path / "worktree")
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
        open_harness(None, tmp_path, "whub-dev", "TASK-095", None)

    run.assert_not_called()


def test_open_harness_uses_the_registered_task_id(tmp_path: Path) -> None:
    registered = SimpleNamespace(
        definition=SimpleNamespace(task_id="TASK-095"), destination=tmp_path
    )
    resolved_auth = SimpleNamespace(auth=SimpleNamespace(variables={}), tools=())
    plan = SimpleNamespace(files={})
    session = SimpleNamespace()

    with (
        patch(
            "whub.services.agent.harness.resolve_project_worktree",
            return_value=registered,
        ),
        patch(
            "whub.services.agent.harness.resolve_agent_auth",
            return_value=resolved_auth,
        ),
        patch("whub.services.agent.harness.render_codex", return_value=plan),
        patch("whub.services.agent.harness.render_claude_code", return_value=plan),
        patch("whub.services.agent.harness.prepare"),
        patch(
            "whub.services.agent.harness._start_tmux_session", return_value=session
        ) as start,
    ):
        assert open_harness(None, tmp_path, "whub-dev", "TASK-095", ()) is session

    assert start.call_args.args[0].task_id == "TASK-095"


def test_close_stops_tmux_before_state_cleanup(tmp_path: Path) -> None:
    registered = SimpleNamespace(
        definition=SimpleNamespace(task_id="TASK-095"), destination=tmp_path
    )
    with (
        patch(
            "whub.services.agent.harness.resolve_project_worktree",
            return_value=registered,
        ),
        patch("whub.services.agent.harness._stop_tmux_session") as stop,
        patch("whub.services.agent.harness.cleanup") as clean,
    ):
        close_harness(None, tmp_path, "whub-dev", "TASK-095")
    assert stop.call_count == 1
    assert clean.call_count == 1
