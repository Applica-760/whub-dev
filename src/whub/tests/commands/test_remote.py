"""Remote CLI group tests."""

from click.testing import CliRunner

from whub.cli import main


def test_remote_group_lists_remote_commands() -> None:
    result = CliRunner().invoke(main, ["remote", "--help"])

    assert result.exit_code == 0
    for command in ("run", "mount", "unmount", "get", "put", "session"):
        assert command in result.output


def test_legacy_top_level_command_is_not_available() -> None:
    result = CliRunner().invoke(main, ["run"])

    assert result.exit_code != 0
    assert "No such command 'run'" in result.output
