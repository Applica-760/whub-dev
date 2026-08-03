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
