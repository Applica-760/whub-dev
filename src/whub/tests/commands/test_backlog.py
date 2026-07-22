"""`whub backlog`コマンドのCLI振る舞いテスト。

検証するケース:
1. Project未指定時はwhub-devへ追記
2. --projectで明示したProjectへ追記
3. 入力メモの前後空白除去
4. 空メモの拒否
5. ServiceErrorのClickException化

検証しないケース:
- local/remoteの書込・マーカー検証（serviceでカバー）
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from whub.commands.backlog import backlog
from whub.services.errors import ServiceError
from whub.tests.helpers import manifest


class TestBacklogCmdSpec:
    def test_defaults_to_whub_dev(self):
        # ケース1
        m = manifest()
        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch("whub.commands.backlog.append_backlog") as mock_append,
        ):
            result = CliRunner().invoke(
                backlog,
                ["add feature X"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "backlog whub-dev: add feature X" in result.output
        mock_append.assert_called_once_with(m, "whub-dev", "add feature X")

    def test_accepts_project_option(self):
        # ケース2
        m = manifest()
        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch("whub.commands.backlog.append_backlog") as mock_append,
        ):
            result = CliRunner().invoke(
                backlog,
                ["add feature X", "--project", "local"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "backlog local: add feature X" in result.output
        mock_append.assert_called_once_with(m, "local", "add feature X")

    def test_strips_memo(self):
        # ケース3
        m = manifest()
        with (
            patch("whub.commands.backlog.get_manifest", return_value=m),
            patch("whub.commands.backlog.append_backlog") as mock_append,
        ):
            result = CliRunner().invoke(
                backlog,
                ["  first memo  ", "--project", "local"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        mock_append.assert_called_once_with(m, "local", "first memo")

    def test_empty_memo_errors(self):
        # ケース4
        with (
            patch("whub.commands.backlog.get_manifest", return_value=manifest()),
            patch("whub.commands.backlog.append_backlog") as mock_append,
        ):
            result = CliRunner().invoke(backlog, [""])

        assert result.exit_code != 0
        assert "memo text is required" in result.output
        mock_append.assert_not_called()

    @pytest.mark.parametrize(
        "message",
        [
            "backlog markers are missing or duplicated",
            "remote backlog failed: ssh failed",
            "resource source does not exist: /tmp/source",
        ],
    )
    def test_service_error_is_rendered(self, message: str):
        # ケース5
        with (
            patch("whub.commands.backlog.get_manifest", return_value=manifest()),
            patch(
                "whub.commands.backlog.append_backlog",
                side_effect=ServiceError(message),
            ),
        ):
            result = CliRunner().invoke(backlog, ["memo", "--project", "local"])

        assert result.exit_code != 0
        assert message in result.output
