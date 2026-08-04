from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.agent import agent
from whub.services.errors import ServiceError


def test_attention_hook_swallows_invalid_input_and_control_failures() -> None:
    invalid = CliRunner().invoke(agent, ["attention-hook"], input="not json")
    assert invalid.exit_code == 0
    assert invalid.output == ""

    with patch(
        "whub.commands.agent.submit_attention_hook",
        side_effect=ServiceError("web app is not running"),
    ):
        failed_control = CliRunner().invoke(
            agent,
            ["attention-hook"],
            input=(
                '{"hook_event_name":"PermissionRequest","session_id":"session-1",'
                '"cwd":"/workspace/worktree","turn_id":"turn-1","tool_name":"Bash"}'
            ),
        )

    assert failed_control.exit_code == 0
    assert failed_control.output == ""


def test_attention_hook_forwards_its_operation_identity(monkeypatch) -> None:
    monkeypatch.setenv("WHUB_OPERATOR_ID", "operator-1")
    with patch("whub.commands.agent.submit_attention_hook") as submit:
        result = CliRunner().invoke(
            agent,
            ["attention-hook"],
            input=(
                '{"hook_event_name":"Stop","session_id":"session-1",'
                '"cwd":"/workspace","turn_id":"turn-1"}'
            ),
        )

    assert result.exit_code == 0
    assert submit.call_args.args[1]["operator_id"] == "operator-1"
