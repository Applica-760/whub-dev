from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from whub.commands.session import session
from whub.models import SessionDescriptor
from whub.services.errors import ServiceError
from whub.tests.helpers import manifest


def descriptor(state: str = "pending") -> SessionDescriptor:
    now = datetime.now(timezone.utc)
    return SessionDescriptor(
        project="remote",
        task="TASK-030",
        run_id="TASK-030-r001",
        state=state,
        created_at=now,
        updated_at=now,
    )


def test_reserve_prints_run_and_gui_command() -> None:
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch(
            "whub.commands.session.reserve_session",
            return_value="TASK-030-r001",
        ),
    ):
        result = CliRunner().invoke(session, ["reserve", "remote", "--task", "030"])
    assert result.exit_code == 0
    assert "reserved remote TASK-030-r001" in result.output
    assert "bash .whub/session-launcher.sh TASK-030-r001" in result.output


def test_ls_renders_run_state() -> None:
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch("whub.commands.session.list_sessions", return_value=[descriptor()]),
    ):
        result = CliRunner().invoke(session, ["ls", "remote"])
    assert result.exit_code == 0
    assert "TASK-030-r001" in result.output
    assert "pending" in result.output


def test_clean_calls_run_scoped_cleanup() -> None:
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch("whub.commands.session.clean_session") as clean,
    ):
        result = CliRunner().invoke(session, ["clean", "remote", "TASK-030-r001"])
    assert result.exit_code == 0
    clean.assert_called_once()
    assert "cleaned remote TASK-030-r001" in result.output


def test_clean_reports_running_run_rejection() -> None:
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch(
            "whub.commands.session.clean_session",
            side_effect=ServiceError("run is still running: TASK-030-r001"),
        ),
    ):
        result = CliRunner().invoke(session, ["clean", "remote", "TASK-030-r001"])
    assert result.exit_code != 0
    assert "run is still running" in result.output


def test_handoff_reads_command_from_stdin() -> None:
    command = 'PATH="$PWD/.venv/bin:$PATH" uv run python probe.py\n'
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch("whub.commands.session.write_session_handoff") as handoff,
    ):
        result = CliRunner().invoke(
            session,
            [
                "handoff",
                "remote",
                "TASK-030-r001",
                "--purpose",
                "Rerun probe",
            ],
            input=command,
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    handoff.assert_called_once_with(
        manifest(), "remote", "TASK-030-r001", "Rerun probe", command
    )
    assert "updated remote .whub/handoff/commands.md" in result.output


def test_handoff_rejects_empty_stdin() -> None:
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch("whub.commands.session.write_session_handoff") as handoff,
    ):
        result = CliRunner().invoke(
            session,
            ["handoff", "remote", "TASK-030-r001", "--purpose", "probe"],
            input=" \n\t",
        )

    assert result.exit_code != 0
    assert "command input is required" in result.output
    handoff.assert_not_called()


def test_handoff_rejects_multiline_purpose() -> None:
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch("whub.commands.session.write_session_handoff") as handoff,
    ):
        result = CliRunner().invoke(
            session,
            ["handoff", "remote", "TASK-030-r001", "--purpose", "one\ntwo"],
            input="echo ok\n",
        )

    assert result.exit_code != 0
    assert "purpose must be one non-empty line" in result.output
    handoff.assert_not_called()


def test_logs_follow_streams_lines_and_strips_ansi() -> None:
    process = MagicMock()
    process.stdout = iter(["\x1b[31mlive line\x1b[0m\n"])
    with (
        patch("whub.commands.session.get_manifest", return_value=manifest()),
        patch("whub.commands.session.build_follow_logs_command", return_value=["ssh"]),
        patch("whub.commands.session.subprocess.Popen", return_value=process),
    ):
        result = CliRunner().invoke(
            session,
            ["logs", "remote", "TASK-030-r001", "--follow"],
        )
    assert result.exit_code == 0
    assert result.output == "live line\n"
    process.wait.assert_called_once()
