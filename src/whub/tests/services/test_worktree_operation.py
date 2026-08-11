from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from whub.services.errors import ServiceError
from whub.services.worktree.operation import (
    _status_paths,
    close_project_worktree,
    create_project_pull_request,
    open_project_worktree,
)


def _worktree(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        project="local",
        task_id="TASK-072",
        branch="tasks/072",
        parent=tmp_path / "source",
        destination=tmp_path / "projects/worktrees/local-072",
        base_branch="main",
        host=None,
        workspace_path=str(tmp_path / "projects/worktrees/local-072"),
    )


def test_open_reuses_branch_then_opens_agent(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    session = SimpleNamespace()
    with (
        patch(
            "whub.services.worktree.operation.resolve_worktree", return_value=worktree
        ),
        patch(
            "whub.services.worktree.operation.resolve_task_worktree",
            return_value=worktree,
        ),
        patch(
            "whub.services.worktree.operation.run_worktree_git",
            side_effect=[CompletedProcess([], 0), CompletedProcess([], 0)],
        ) as git,
        patch(
            "whub.services.worktree.operation.open_agent", return_value=session
        ) as open_agent,
    ):
        assert (
            open_project_worktree(None, tmp_path, "local", "TASK-072", ("implementer",))
            is session
        )

    assert git.call_args_list[1].args[2:] == (
        "worktree",
        "add",
        str(worktree.destination),
        "tasks/072",
    )
    open_agent.assert_called_once_with(
        None, tmp_path, "local", "TASK-072", ("implementer",)
    )


def test_open_reuses_existing_worktree_without_git_lifecycle(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    worktree.destination.mkdir(parents=True)
    session = SimpleNamespace()
    with (
        patch(
            "whub.services.worktree.operation.resolve_worktree", return_value=worktree
        ),
        patch("whub.services.worktree.operation.run_worktree_git") as git,
        patch(
            "whub.services.worktree.operation.open_agent", return_value=session
        ) as open_agent,
    ):
        assert (
            open_project_worktree(None, tmp_path, "local", "TASK-072", ("implementer",))
            is session
        )

    git.assert_not_called()
    open_agent.assert_called_once_with(
        None, tmp_path, "local", "TASK-072", ("implementer",)
    )


def test_open_rolls_back_only_new_branch_when_agent_open_fails(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    with (
        patch(
            "whub.services.worktree.operation.resolve_worktree", return_value=worktree
        ),
        patch(
            "whub.services.worktree.operation.resolve_task_worktree",
            return_value=worktree,
        ),
        patch(
            "whub.services.worktree.operation.run_worktree_git",
            side_effect=[
                CompletedProcess([], 1),
                CompletedProcess([], 0),
                CompletedProcess([], 0),
                CompletedProcess([], 0),
            ],
        ) as git,
        patch(
            "whub.services.worktree.operation.open_agent",
            side_effect=ServiceError("auth failed"),
        ),
        pytest.raises(ServiceError, match="auth failed"),
    ):
        open_project_worktree(None, tmp_path, "local", "TASK-072", ("implementer",))

    assert git.call_args_list[2].args[2:] == (
        "worktree",
        "remove",
        str(worktree.destination),
    )
    assert git.call_args_list[3].args[2:] == ("branch", "-D", "tasks/072")


def test_close_ignores_only_unchanged_agent_files_then_merges(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    status = CompletedProcess([], 0, "?? .codex/config.toml\0", "")
    with (
        patch(
            "whub.services.worktree.operation.resolve_project_worktree",
            return_value=worktree,
        ),
        patch(
            "whub.services.worktree.operation.run_worktree_git",
            side_effect=[
                status,
                CompletedProcess([], 0, "", ""),
                CompletedProcess([], 0, "abc123\n", ""),
                CompletedProcess([], 0, "", ""),
            ],
        ) as git,
        patch(
            "whub.services.worktree.operation.unchanged_generated_paths",
            return_value={Path(".codex/config.toml")},
        ),
        patch(
            "whub.services.worktree.operation._run_gh",
            side_effect=[
                CompletedProcess(
                    [], 0, '[{"url":"https://example/pr/72","headRefOid":"abc123"}]', ""
                ),
                CompletedProcess([], 0, "", ""),
                CompletedProcess([], 0, "MERGED\n", ""),
            ],
        ) as gh,
        patch("whub.services.worktree.operation.close_agent") as close_agent,
    ):
        assert (
            close_project_worktree(None, tmp_path, "local", "TASK-072")
            == "https://example/pr/72"
        )

    assert git.call_args_list[1].args[2:] == (
        "push",
        "--set-upstream",
        "origin",
        "tasks/072",
    )
    assert gh.call_args_list[1].args[1:6] == (
        "pr",
        "merge",
        "https://example/pr/72",
        "--merge",
        "--match-head-commit",
    )
    close_agent.assert_called_once_with(None, tmp_path, "local", "TASK-072")


def test_pr_ignores_unchanged_agent_files_without_cleanup_or_merge(
    tmp_path: Path,
) -> None:
    worktree = _worktree(tmp_path)
    status = CompletedProcess([], 0, "?? .codex/config.toml\0", "")
    with (
        patch(
            "whub.services.worktree.operation.resolve_project_worktree",
            return_value=worktree,
        ),
        patch(
            "whub.services.worktree.operation.run_worktree_git",
            side_effect=[
                status,
                CompletedProcess([], 0, "", ""),
                CompletedProcess([], 0, "abc123\n", ""),
            ],
        ) as git,
        patch(
            "whub.services.worktree.operation.unchanged_generated_paths",
            return_value={Path(".codex/config.toml")},
        ),
        patch(
            "whub.services.worktree.operation._run_gh",
            return_value=CompletedProcess(
                [], 0, '[{"url":"https://example/pr/72","headRefOid":"abc123"}]', ""
            ),
        ) as gh,
        patch("whub.services.worktree.operation.close_agent") as close_agent,
    ):
        assert (
            create_project_pull_request(None, tmp_path, "local", "TASK-072")
            == "https://example/pr/72"
        )

    assert git.call_args_list[1].args[2:] == (
        "push",
        "--set-upstream",
        "origin",
        "tasks/072",
    )
    assert gh.call_args_list[0].args[1:3] == ("pr", "list")
    close_agent.assert_not_called()


def test_close_keeps_worktree_when_non_agent_change_exists(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    with (
        patch(
            "whub.services.worktree.operation.resolve_project_worktree",
            return_value=worktree,
        ),
        patch(
            "whub.services.worktree.operation.run_worktree_git",
            return_value=CompletedProcess([], 0, " M app.py\0", ""),
        ) as git,
        patch(
            "whub.services.worktree.operation.unchanged_generated_paths",
            return_value=set(),
        ),
        pytest.raises(ServiceError, match="worktree has uncommitted changes"),
    ):
        close_project_worktree(None, tmp_path, "local", "TASK-072")

    assert git.call_count == 1


def test_close_stops_before_merge_when_agent_cleanup_fails(tmp_path: Path) -> None:
    worktree = _worktree(tmp_path)
    with (
        patch(
            "whub.services.worktree.operation.resolve_project_worktree",
            return_value=worktree,
        ),
        patch(
            "whub.services.worktree.operation.run_worktree_git",
            side_effect=[
                CompletedProcess([], 0, "", ""),
                CompletedProcess([], 0, "", ""),
                CompletedProcess([], 0, "abc123\n", ""),
            ],
        ),
        patch(
            "whub.services.worktree.operation.unchanged_generated_paths",
            return_value=set(),
        ),
        patch("whub.services.worktree.operation._run_gh") as gh,
        patch(
            "whub.services.worktree.operation.close_agent",
            side_effect=ServiceError("config changed"),
        ),
        pytest.raises(ServiceError, match="config changed"),
    ):
        close_project_worktree(None, tmp_path, "local", "TASK-072")

    gh.assert_not_called()


def test_status_paths_preserves_renamed_paths() -> None:
    assert _status_paths("R  new.py\0old.py\0") == ["new.py", "old.py"]
