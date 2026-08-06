from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from subprocess import CompletedProcess
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from whub.models import Host, RemoteResource
from whub.services.agent.agent import close_agent
from whub.services.agent.codex import trust as codex_trust
from whub.services.agent import remote_state
from whub.services.agent.tmux_session import close_tmux_session
from whub.services.errors import ServiceError


def _host() -> Host:
    return Host(
        hostname="ssh.test.invalid",
        user="test-user",
        identity_file="/test/identity",
        mount_root="/srv",
    )


@pytest.mark.parametrize("returncode", [127, 255])
def test_remote_tmux_probe_failure_is_not_missing(returncode: int) -> None:
    with (
        patch(
            "whub.services.agent.tmux_session.run_ssh_command",
            return_value=CompletedProcess([], returncode, "", "probe failed"),
        ),
        pytest.raises(ServiceError, match="failed to inspect remote tmux"),
    ):
        close_tmux_session("whub-dev", "TASK-120", _host())


def test_remote_tmux_confirmed_missing_is_idempotent() -> None:
    with patch(
        "whub.services.agent.tmux_session.run_ssh_command",
        return_value=CompletedProcess([], 1, "", "missing"),
    ) as run:
        close_tmux_session("whub-dev", "TASK-120", _host())

    assert run.call_count == 1


def test_remote_close_preserves_state_when_tmux_probe_fails(tmp_path: Path) -> None:
    registered = SimpleNamespace(
        definition=SimpleNamespace(task_id="TASK-120"),
        destination="/srv/worktrees/whub-dev-120",
        host=_host(),
    )
    resource = RemoteResource(
        type="remote",
        host="home",
        path="whub-dev",
        workspace_path="whub-dev",
    )
    with (
        patch(
            "whub.services.agent.agent.resolve_project_worktree",
            return_value=registered,
        ),
        patch(
            "whub.services.agent.agent.resolve_project_resource",
            return_value=resource,
        ),
        patch(
            "whub.services.agent.tmux_session.run_ssh_command",
            return_value=CompletedProcess([], 255, "", "ssh failed"),
        ),
        patch("whub.services.agent.agent.cleanup_remote_codex_trust") as trust,
        patch("whub.services.agent.agent.remote_state.cleanup") as remote_state,
        pytest.raises(ServiceError, match="failed to inspect remote tmux"),
    ):
        close_agent(None, tmp_path, "whub-dev", "TASK-120")

    trust.assert_not_called()
    remote_state.assert_not_called()


def test_remote_state_cleanup_keeps_state_on_ssh_failure(tmp_path: Path) -> None:
    state_path = remote_state._state_path(tmp_path, "whub-dev", "TASK-120")
    remote_state._save(
        state_path,
        {
            "worktree": "/srv/worktrees/whub-dev-120",
            "files": {".codex/config.toml": "digest"},
            "blocks": {},
        },
    )

    def run(_host: Host, command: str) -> CompletedProcess[str]:
        if command.startswith("test ! -L"):
            return CompletedProcess([], 0, "", "")
        return CompletedProcess([], 255, "", "ssh failed")

    with (
        patch("whub.services.agent.remote_state.run_ssh_command", side_effect=run),
        pytest.raises(ServiceError, match="remote Agent state operation failed"),
    ):
        remote_state.cleanup(
            tmp_path,
            "whub-dev",
            "TASK-120",
            _host(),
            "/srv/worktrees/whub-dev-120",
        )

    assert state_path.exists()


def test_remote_state_reports_owned_files_and_blocks(tmp_path: Path) -> None:
    state_path = remote_state._state_path(tmp_path, "whub-dev", "TASK-120")
    remote_state._save(
        state_path,
        {
            "worktree": "/srv/worktrees/whub-dev-120",
            "files": {".codex/config.toml": "digest"},
            "blocks": {"AGENTS.md": "digest"},
        },
    )

    assert remote_state.owned_paths(
        tmp_path,
        "whub-dev",
        "TASK-120",
        "/srv/worktrees/whub-dev-120",
    ) == {
        PurePosixPath(".codex/config.toml"),
        PurePosixPath("AGENTS.md"),
    }


def test_remote_state_cleanup_accepts_confirmed_missing_owned_files(
    tmp_path: Path,
) -> None:
    state_path = remote_state._state_path(tmp_path, "whub-dev", "TASK-120")
    remote_state._save(
        state_path,
        {
            "worktree": "/srv/worktrees/whub-dev-120",
            "files": {".codex/config.toml": "digest"},
            "blocks": {"AGENTS.md": "digest"},
        },
    )

    def run(_host: Host, command: str) -> CompletedProcess[str]:
        return CompletedProcess([], 0 if command.startswith("test ! -L") else 1, "", "")

    with patch("whub.services.agent.remote_state.run_ssh_command", side_effect=run):
        remote_state.cleanup(
            tmp_path,
            "whub-dev",
            "TASK-120",
            _host(),
            "/srv/worktrees/whub-dev-120",
        )

    assert not state_path.exists()


class _ConcurrentRemoteConfig:
    def __init__(self) -> None:
        self.path = "/home/test-user/.codex/config.toml"
        self.content: str | None = None
        self.lock = threading.Lock()
        self.owner: int | None = None

    def run(self, _host: Host, command: str, **_kwargs) -> CompletedProcess[str]:
        if command == 'printf %s "$HOME/.codex/config.toml"':
            return CompletedProcess([], 0, self.path, "")
        if "while ! mkdir" in command:
            if not self.lock.acquire(timeout=1):
                return CompletedProcess([], 75, "", "")
            self.owner = threading.get_ident()
            return CompletedProcess([], 0, "", "")
        if command.startswith("rmdir --"):
            self._assert_locked()
            self.owner = None
            self.lock.release()
            return CompletedProcess([], 0, "", "")
        if command.startswith("test -e"):
            self._assert_locked()
            return CompletedProcess([], 0 if self.content is not None else 1, "", "")
        if command.startswith("cat --"):
            self._assert_locked()
            return CompletedProcess([], 0, self.content or "", "")
        if command.startswith("mkdir -p --"):
            self._assert_locked()
            return CompletedProcess([], 0, "", "")
        raise AssertionError(f"unexpected remote command: {command}")

    def write(
        self, _host: Host, path: str, content: str, **_kwargs
    ) -> CompletedProcess[str]:
        self._assert_locked()
        assert path == self.path
        self.content = content
        return CompletedProcess([], 0, "", "")

    def _assert_locked(self) -> None:
        assert self.owner == threading.get_ident()


def test_remote_codex_trust_serializes_concurrent_updates(tmp_path: Path) -> None:
    remote = _ConcurrentRemoteConfig()
    barrier = threading.Barrier(2)

    def prepare(task: str, worktree: str) -> None:
        barrier.wait()
        codex_trust.prepare_remote(tmp_path, "remote", task, _host(), worktree)

    with (
        patch(
            "whub.services.agent.codex.trust.run_ssh_command",
            side_effect=remote.run,
        ),
        patch(
            "whub.services.agent.codex.trust.remote_write_file",
            side_effect=remote.write,
        ),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        futures = (
            executor.submit(prepare, "TASK-120", "/srv/worktrees/remote-120"),
            executor.submit(prepare, "TASK-121", "/srv/worktrees/remote-121"),
        )
        for future in futures:
            future.result()

    assert remote.content is not None
    assert "/srv/worktrees/remote-120" in remote.content
    assert "/srv/worktrees/remote-121" in remote.content


def test_remote_codex_cleanup_keeps_state_on_ssh_failure(tmp_path: Path) -> None:
    state_path = codex_trust._remote_state_path(tmp_path, "remote", "TASK-120")
    codex_trust._save_remote_state(
        state_path,
        {
            "config_path": "/home/test-user/.codex/config.toml",
            "worktree": "/srv/worktrees/remote-120",
            "block": "owned block",
        },
    )

    def run(_host: Host, command: str, **_kwargs) -> CompletedProcess[str]:
        if "while ! mkdir" in command or command.startswith("rmdir --"):
            return CompletedProcess([], 0, "", "")
        return CompletedProcess([], 255, "", "ssh failed")

    with (
        patch(
            "whub.services.agent.codex.trust.run_ssh_command",
            side_effect=run,
        ),
        pytest.raises(ServiceError, match="remote Codex trust operation failed"),
    ):
        codex_trust.cleanup_remote(
            tmp_path,
            "remote",
            "TASK-120",
            _host(),
            "/srv/worktrees/remote-120",
        )

    assert state_path.exists()
