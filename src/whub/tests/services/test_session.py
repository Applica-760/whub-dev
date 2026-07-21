from datetime import datetime, timezone
from importlib.resources import as_file, files
import json
import subprocess
from unittest.mock import patch

import pytest

from whub.services.errors import ServiceError
from whub.services.session import (
    clean_session,
    get_session,
    list_sessions,
    reserve_session,
    write_session_handoff,
)
from whub.tests.helpers import manifest


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
    completed = subprocess.CompletedProcess(["ssh"], 0, stdout="TASK-030-r001\n", stderr="")
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
    command = "PATH=\"$PWD/.venv/bin:$PATH\" uv run python - <<'PY'\nprint(`value`)\nPY\n"
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
        write_session_handoff(
            manifest(), "remote", "TASK-030-r001", purpose, "echo ok"
        )
    run.assert_not_called()


def test_handoff_rejects_empty_command_before_ssh() -> None:
    with (
        patch("whub.services.session.run_ssh_command") as run,
        pytest.raises(ServiceError, match="command"),
    ):
        write_session_handoff(
            manifest(), "remote", "TASK-030-r001", "probe", " \n\t"
        )
    run.assert_not_called()


def test_handoff_rejects_local_resource() -> None:
    with pytest.raises(ServiceError, match="not a remote resource"):
        write_session_handoff(
            manifest(), "local", "TASK-030-r001", "probe", "echo ok"
        )


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
        write_session_handoff(
            manifest(), "remote", "TASK-999-r001", "probe", "echo ok"
        )


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
