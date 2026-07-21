from datetime import datetime, timezone
from importlib.resources import as_file, files
import json
from pathlib import Path
import stat
import subprocess
import sys
from unittest.mock import patch

import pytest

from whub.services.errors import ServiceError
from whub.services.session import (
    _HANDOFF,
    clean_session,
    get_session,
    list_sessions,
    reserve_session,
    write_session_handoff,
)
from whub.tests.helpers import manifest


def run_handoff_script(root: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _HANDOFF, str(root), payload["run_id"]],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def prepare_handoff_run(root: Path, run_id: str = "TASK-036-r001") -> None:
    sessions = root / ".whub" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / f"{run_id}.yaml").write_text("state: pending\n")


def descriptor() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1,
        "protocol_version": 1,
        "project": "remote",
        "task": "TASK-030",
        "run_id": "TASK-030-r001",
        "state": "pending",
        "created_at": now,
        "updated_at": now,
        "tmux": None,
        "panes": [],
    }


def test_reserve_uses_ssh_and_normalizes_task_id() -> None:
    completed = subprocess.CompletedProcess(
        ["ssh"], 0, stdout="TASK-030-r001\n", stderr=""
    )
    with patch("whub.services.session.run_ssh_command", return_value=completed) as run:
        run_id = reserve_session(manifest(), "remote", "30")
    assert run_id == "TASK-030-r001"
    payload = json.loads(run.call_args.kwargs["input"])
    assert payload["task"] == "TASK-030"
    assert "PyYAML is required" in payload["assets"]["session-launcher.py"]
    assert "session-launcher.py" in payload["assets"]["session-launcher.sh"]


def test_list_validates_remote_descriptors() -> None:
    completed = subprocess.CompletedProcess(
        ["ssh"], 0, stdout=json.dumps([descriptor()]), stderr=""
    )
    with patch("whub.services.session.run_ssh_command", return_value=completed):
        items = list_sessions(manifest(), "remote")
    assert [item.run_id for item in items] == ["TASK-030-r001"]


def test_clean_delegates_to_remote_operation() -> None:
    completed = subprocess.CompletedProcess(["ssh"], 0, stdout="", stderr="")
    with patch("whub.services.session.run_ssh_command", return_value=completed) as run:
        clean_session(manifest(), "remote", "TASK-030-r001")
    assert "TASK-030-r001" in run.call_args.args[1]


def test_handoff_sends_command_as_json_over_ssh() -> None:
    command = (
        "PATH=\"$PWD/.venv/bin:$PATH\" uv run python - <<'PY'\nprint(`value`)\nPY\n"
    )
    completed = subprocess.CompletedProcess(["ssh"], 0, stdout="", stderr="")
    with patch("whub.services.session.run_ssh_command", return_value=completed) as run:
        write_session_handoff(
            manifest(),
            "remote",
            "TASK-030-r001",
            "Rerun probe",
            command,
        )

    payload = json.loads(run.call_args.kwargs["input"])
    assert payload["run_id"] == "TASK-030-r001"
    assert payload["purpose"] == "Rerun probe"
    assert payload["command"] == command
    assert payload["timestamp"].endswith(" JST")


@pytest.mark.parametrize("purpose", ["", "   ", "line one\nline two"])
def test_handoff_rejects_invalid_purpose_before_ssh(purpose: str) -> None:
    with (
        patch("whub.services.session.run_ssh_command") as run,
        pytest.raises(ServiceError, match="purpose"),
    ):
        write_session_handoff(manifest(), "remote", "TASK-030-r001", purpose, "echo ok")
    run.assert_not_called()


def test_handoff_rejects_empty_command_before_ssh() -> None:
    with (
        patch("whub.services.session.run_ssh_command") as run,
        pytest.raises(ServiceError, match="command"),
    ):
        write_session_handoff(manifest(), "remote", "TASK-030-r001", "probe", " \n\t")
    run.assert_not_called()


def test_handoff_rejects_local_resource() -> None:
    with pytest.raises(ServiceError, match="not a remote resource"):
        write_session_handoff(manifest(), "local", "TASK-030-r001", "probe", "echo ok")


def test_handoff_reports_unknown_remote_run() -> None:
    error = subprocess.CalledProcessError(
        1,
        ["ssh"],
        output="",
        stderr="unknown run: TASK-999-r001\n",
    )
    with (
        patch("whub.services.session.run_ssh_command", side_effect=error),
        pytest.raises(ServiceError, match="unknown run: TASK-999-r001"),
    ):
        write_session_handoff(manifest(), "remote", "TASK-999-r001", "probe", "echo ok")


def test_handoff_script_prepends_exact_markdown_and_preserves_existing_bytes(
    tmp_path: Path,
) -> None:
    prepare_handoff_run(tmp_path)
    handoff = tmp_path / ".whub" / "handoff"
    handoff.mkdir()
    commands = handoff / "commands.md"
    commands.write_bytes(b"legacy\r\n")
    command = (
        "PATH=\"$PWD/.venv/bin:$PATH\" uv run python - <<'PY'\n"
        "print('quote \\\\ and ``` and 日本語')\n"
        "PY\n"
    )
    payload = {
        "run_id": "TASK-036-r001",
        "purpose": "Rerun probe",
        "command": command,
        "timestamp": "2026-07-21 12:34:56 JST",
    }

    result = run_handoff_script(tmp_path, payload)

    assert result.returncode == 0, result.stderr
    first_content = (
        b"## 2026-07-21 12:34:56 JST | TASK-036-r001 | Rerun probe\n\n"
        + b"````bash\n"
        + command.encode()
        + b"````\n\nlegacy\r\n"
    )
    assert commands.read_bytes() == first_content
    assert stat.S_IMODE(handoff.stat().st_mode) == 0o700
    assert stat.S_IMODE(commands.stat().st_mode) == 0o600
    assert stat.S_IMODE((handoff / "commands.lock").stat().st_mode) == 0o600

    newer = {
        "run_id": "TASK-036-r001",
        "purpose": "Latest probe",
        "command": "echo latest",
        "timestamp": "2026-07-21 12:35:00 JST",
    }
    result = run_handoff_script(tmp_path, newer)

    assert result.returncode == 0, result.stderr
    assert commands.read_bytes() == (
        b"## 2026-07-21 12:35:00 JST | TASK-036-r001 | Latest probe\n\n"
        b"```bash\necho latest\n```\n\n" + first_content
    )


def test_handoff_script_serializes_concurrent_updates(tmp_path: Path) -> None:
    prepare_handoff_run(tmp_path)
    processes: list[subprocess.Popen[str]] = []
    for number in range(8):
        payload = {
            "run_id": "TASK-036-r001",
            "purpose": f"probe {number}",
            "command": f"echo command-{number}",
            "timestamp": f"2026-07-21 12:34:{number:02} JST",
        }
        process = subprocess.Popen(
            [sys.executable, "-c", _HANDOFF, str(tmp_path), payload["run_id"]],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdin is not None
        process.stdin.write(json.dumps(payload))
        process.stdin.close()
        processes.append(process)

    for process in processes:
        assert process.wait() == 0

    content = (tmp_path / ".whub" / "handoff" / "commands.md").read_text()
    assert content.count("\n## ") + content.startswith("## ") == 8
    for number in range(8):
        assert f"| probe {number}\n" in content
        assert f"echo command-{number}\n" in content


def test_session_rejects_local_resource() -> None:
    with pytest.raises(ServiceError, match="not a remote resource"):
        reserve_session(manifest(), "local")


def test_session_rejects_unsafe_run_id_before_ssh() -> None:
    with (
        patch("whub.services.session.run_ssh_command") as run,
        pytest.raises(ServiceError, match="invalid run ID"),
    ):
        get_session(manifest(), "remote", "../escape")
    run.assert_not_called()


def test_packaged_launcher_has_valid_bash_syntax() -> None:
    resource = files("whub").joinpath("session/launcher.sh")
    with as_file(resource) as path:
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_packaged_launcher_helper_has_valid_python_syntax() -> None:
    resource = files("whub").joinpath("session/launcher.py")
    source = resource.read_text()
    compile(source, str(resource), "exec")
