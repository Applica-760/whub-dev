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
from whub.services.agent.state import cleanup, load, prepare, state_path


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


def test_state_does_not_claim_matching_existing_text_config(tmp_path: Path) -> None:
    path = tmp_path / ".codex/config.toml"
    path.parent.mkdir()
    path.write_text('sandbox_mode = "workspace-write"\n')

    prepare(tmp_path, "whub-dev", "TASK-095", tmp_path, _plan().files)
    cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)

    assert path.exists()
    assert not state_path(tmp_path, "whub-dev", "TASK-095").exists()


def test_state_preserves_modified_owned_config_and_state(tmp_path: Path) -> None:
    prepare(tmp_path, "whub-dev", "TASK-095", tmp_path, _plan().files)
    path = tmp_path / ".codex/config.toml"
    path.write_text("# user change\n")

    with pytest.raises(
        ServiceError, match="generated config was modified and was not removed"
    ):
        cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)

    assert path.read_text() == "# user change\n"
    assert state_path(tmp_path, "whub-dev", "TASK-095").exists()


def test_state_removes_generic_empty_parent_directories(tmp_path: Path) -> None:
    keep = tmp_path / "provider/keep.txt"
    keep.parent.mkdir()
    keep.write_text("keep\n")
    relative = PurePosixPath("provider/generated/nested/config.txt")

    prepare(
        tmp_path,
        "whub-dev",
        "TASK-095",
        tmp_path,
        {relative: "owned\n"},
    )
    cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)

    assert not (tmp_path / relative).exists()
    assert not (tmp_path / "provider/generated").exists()
    assert keep.exists()


def test_state_injects_and_cleans_owned_block_from_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# Project rules\n")
    block = "<!-- whub:harness:context:start -->\nHub rules\n<!-- whub:harness:context:end -->\n"

    prepare(
        tmp_path,
        "whub-dev",
        "TASK-095",
        tmp_path,
        {},
        patches={PurePosixPath("AGENTS.md"): block},
    )

    assert path.read_text() == "# Project rules\n\n" + block
    cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)

    assert path.read_text() == "# Project rules\n"
    assert not state_path(tmp_path, "whub-dev", "TASK-095").exists()


def test_state_preserves_external_edits_when_cleaning_owned_block(tmp_path: Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# Project rules\n")
    block = "<!-- whub:harness:context:start -->\nHub rules\n<!-- whub:harness:context:end -->\n"
    prepare(
        tmp_path,
        "whub-dev",
        "TASK-095",
        tmp_path,
        {},
        patches={PurePosixPath("AGENTS.md"): block},
    )
    path.write_text(path.read_text() + "\n# User note\n")

    cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)

    assert path.read_text() == "# Project rules\n\n# User note\n"


def test_state_rejects_changed_owned_block(tmp_path: Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# Project rules\n")
    block = "<!-- whub:harness:context:start -->\nHub rules\n<!-- whub:harness:context:end -->\n"
    prepare(
        tmp_path,
        "whub-dev",
        "TASK-095",
        tmp_path,
        {},
        patches={PurePosixPath("AGENTS.md"): block},
    )
    path.write_text(path.read_text().replace("Hub rules", "Changed rules"))

    with pytest.raises(ServiceError, match="managed context was modified"):
        cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)


def test_state_removes_owned_block_file_when_it_is_empty(tmp_path: Path) -> None:
    block = "<!-- whub:harness:context:start -->\n@../AGENTS.md\n<!-- whub:harness:context:end -->\n"
    prepare(
        tmp_path,
        "whub-dev",
        "TASK-095",
        tmp_path,
        {},
        patches={PurePosixPath(".claude/CLAUDE.md"): block},
    )

    cleanup(tmp_path, "whub-dev", "TASK-095", tmp_path)

    assert not (tmp_path / ".claude/CLAUDE.md").exists()
    assert not (tmp_path / ".claude").exists()


def test_prepare_projects_hub_context(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Hub rules\n")
    skill = tmp_path / ".agents/skills/issue-log"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: issue-log\n---\n")
    (skill / "reference.md").write_text("reference\n")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "AGENTS.md").write_text("# Project rules\n")

    prepare(tmp_path, "whub-dev", "TASK-095", worktree, {})

    assert (worktree / ".agents/skills/issue-log/SKILL.md").read_text() == (
        "---\nname: issue-log\n---\n"
    )
    assert (worktree / ".agents/skills/issue-log/reference.md").read_text() == (
        "reference\n"
    )
    assert "# Hub rules" in (worktree / "AGENTS.md").read_text()
    assert (worktree / ".claude/CLAUDE.md").read_text() == (
        "<!-- whub:harness:context:start -->\n"
        "@../AGENTS.md\n"
        "<!-- whub:harness:context:end -->\n"
    )

    cleanup(tmp_path, "whub-dev", "TASK-095", worktree)

    assert (worktree / "AGENTS.md").read_text() == "# Project rules\n"
    assert not (worktree / ".agents").exists()
    assert not (worktree / ".claude").exists()


def test_state_loads_v1_without_patches(tmp_path: Path) -> None:
    path = state_path(tmp_path, "whub-dev", "TASK-095")
    path.parent.mkdir(parents=True)
    path.write_text(
        "schema_version: 1\n"
        "project: whub-dev\n"
        "task_id: TASK-095\n"
        "worktree: /tmp/worktree\n"
        "files: {}\n"
    )

    state = load(path)

    assert state is not None
    assert state.patches == {}


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


def test_open_harness_projects_hub_context_without_harness_specific_logic(
    tmp_path: Path,
) -> None:
    (tmp_path / "AGENTS.md").write_text("# Hub rules\n")
    skill = tmp_path / ".agents/skills/issue-log"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: issue-log\n---\n")
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "AGENTS.md").write_text("# Project rules\n")
    registered = SimpleNamespace(
        definition=SimpleNamespace(task_id="TASK-095"), destination=worktree
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
        patch("whub.services.agent.harness._start_tmux_session", return_value=session),
    ):
        assert open_harness(None, tmp_path, "whub-dev", "TASK-095", ()) is session

    assert "# Hub rules" in (worktree / "AGENTS.md").read_text()
    assert (worktree / ".agents/skills/issue-log/SKILL.md").exists()
    assert (worktree / ".claude/CLAUDE.md").exists()


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


def test_close_without_tmux_cleans_state_and_is_idempotent(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    prepare(tmp_path, "whub-dev", "TASK-095", worktree, _plan().files)
    registered = SimpleNamespace(
        definition=SimpleNamespace(task_id="TASK-095"), destination=worktree
    )

    with (
        patch(
            "whub.services.agent.harness.resolve_project_worktree",
            return_value=registered,
        ),
        patch(
            "whub.services.agent.harness.subprocess.run",
            return_value=CompletedProcess([], 1, "", "missing"),
        ) as run,
    ):
        close_harness(None, tmp_path, "whub-dev", "TASK-095")
        close_harness(None, tmp_path, "whub-dev", "TASK-095")

    assert run.call_count == 2
    assert not (worktree / ".codex/config.toml").exists()
    assert not state_path(tmp_path, "whub-dev", "TASK-095").exists()


def test_close_tmux_stop_failure_does_not_cleanup_state(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    prepare(tmp_path, "whub-dev", "TASK-095", worktree, _plan().files)
    registered = SimpleNamespace(
        definition=SimpleNamespace(task_id="TASK-095"), destination=worktree
    )

    with (
        patch(
            "whub.services.agent.harness.resolve_project_worktree",
            return_value=registered,
        ),
        patch(
            "whub.services.agent.harness.subprocess.run",
            side_effect=[
                CompletedProcess([], 0, "", ""),
                CompletedProcess([], 1, "", "kill failed"),
            ],
        ),
        pytest.raises(ServiceError, match="failed to stop tmux session: kill failed"),
    ):
        close_harness(None, tmp_path, "whub-dev", "TASK-095")

    assert (worktree / ".codex/config.toml").exists()
    assert state_path(tmp_path, "whub-dev", "TASK-095").exists()


def test_open_restarts_missing_tmux_without_replacing_state(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    registered = SimpleNamespace(
        definition=SimpleNamespace(task_id="TASK-095"), destination=worktree
    )
    resolved_auth = SimpleNamespace(auth=SimpleNamespace(variables={}), tools=())
    empty_plan = SimpleNamespace(files={})

    with (
        patch(
            "whub.services.agent.harness.resolve_project_worktree",
            return_value=registered,
        ),
        patch(
            "whub.services.agent.harness.resolve_agent_auth",
            return_value=resolved_auth,
        ),
        patch("whub.services.agent.harness.render_codex", return_value=_plan()),
        patch(
            "whub.services.agent.harness.render_claude_code",
            return_value=empty_plan,
        ),
        patch(
            "whub.services.agent.harness.subprocess.run",
            side_effect=[
                CompletedProcess([], 1, "", "missing"),
                CompletedProcess([], 0, "", ""),
                CompletedProcess([], 1, "", "missing"),
                CompletedProcess([], 0, "", ""),
            ],
        ) as run,
    ):
        first = open_harness(None, tmp_path, "whub-dev", "TASK-095", ())
        saved_state = state_path(tmp_path, "whub-dev", "TASK-095").read_text()
        second = open_harness(None, tmp_path, "whub-dev", "TASK-095", ())

    assert first == second
    assert run.call_count == 4
    assert (worktree / ".codex/config.toml").read_text() == (
        'sandbox_mode = "workspace-write"\n'
    )
    assert state_path(tmp_path, "whub-dev", "TASK-095").read_text() == saved_state
