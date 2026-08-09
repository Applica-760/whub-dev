"""S1 web application server tests.

検証するケース:
1. health APIが正常応答を返す
2. dist配下の静的ファイルを返す
3. 非APIの未マッチパスはSPAフォールバックする
4. 未定義のAPIパスはSPAフォールバックしない
5. package dist欠如時に明示エラーを返す
6. 常駐子プロセスを指定portで起動する
7. 起動済みサーバーを再利用する
8. downが管理PIDを停止する
9. downが必要に応じてSIGKILLへ昇格する
10. downが未起動時に成功する
11. app PIDがcontext root配下のPIDファイルを使う

検証しないケース:
- 実際の常駐プロセス起動・停止（統合確認で検証）
"""

from __future__ import annotations

import signal
import subprocess
from types import SimpleNamespace
from unittest.mock import call, patch

from click.testing import CliRunner
from fastapi.testclient import TestClient

from whub.commands.app import _stop_process_groups, app
from whub.core.context import WhubContext
from whub.webapp.resources import AppResourceError
from whub.webapp.runner import AppProcessRecord
from whub.webapp.server import create_app


def _dist_dir(tmp_path):
    dist_dir = tmp_path / "dist"
    (dist_dir / "assets").mkdir(parents=True)
    (dist_dir / "index.html").write_text("<main>whub</main>")
    (dist_dir / "assets" / "app.js").write_text("console.log('whub')")
    return dist_dir


def _app_context(tmp_path):
    return SimpleNamespace(
        app_pid_path=tmp_path / "app.pid",
        app_dev_pid_path=tmp_path / "app-dev.pid",
    )


class TestWebappServer:
    def test_app_pid_paths_use_context_directory(self, tmp_path):
        # ケース10
        context = WhubContext(tmp_path)

        assert context.app_pid_path == tmp_path / "app.pid"
        assert context.app_dev_pid_path == tmp_path / "app-dev.pid"

    def test_health(self, tmp_path):
        # ケース1
        client = TestClient(create_app(_dist_dir(tmp_path)))

        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_serves_static_file_and_spa_fallback(self, tmp_path):
        # ケース2,3
        client = TestClient(create_app(_dist_dir(tmp_path)))

        static_response = client.get("/assets/app.js")
        fallback_response = client.get("/todos")

        assert static_response.text == "console.log('whub')"
        assert fallback_response.text == "<main>whub</main>"

    def test_unknown_api_path_does_not_use_spa_fallback(self, tmp_path):
        # ケース4
        client = TestClient(create_app(_dist_dir(tmp_path)))

        response = client.get("/api/unknown")

        assert response.status_code == 404


class TestAppCommand:
    def test_stop_process_groups_kills_remaining_development_group(self):
        with (
            patch("whub.commands.app.os.getpgid", return_value=42),
            patch("whub.commands.app.os.killpg") as killpg,
            patch("whub.commands.app.time.sleep"),
        ):
            _stop_process_groups({"vite": 42})

        assert killpg.call_args_list == [
            call(42, signal.SIGTERM),
            call(42, 0),
            call(42, signal.SIGKILL),
        ]

    def test_missing_package_dist_is_rejected(self, tmp_path):
        # ケース5
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app.packaged_app_dist",
                side_effect=AppResourceError("web app distribution is missing"),
            ),
        ):
            result = CliRunner().invoke(app)

        assert result.exit_code != 0
        assert "web app distribution is missing" in result.output

    def test_starts_detached_server_with_requested_port(self, tmp_path):
        # ケース6,9
        dist_dir = _dist_dir(tmp_path)
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch("whub.commands.app.packaged_app_dist", return_value=dist_dir),
            patch("whub.commands.app._read_running_process", return_value=None),
            patch("whub.commands.app.subprocess.Popen") as mock_popen,
        ):
            result = CliRunner().invoke(app, ["--port", "9000"])

        assert result.exit_code == 0
        assert "app starting: http://127.0.0.1:9000" in result.output
        assert mock_popen.call_args.kwargs == {
            "start_new_session": True,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        assert mock_popen.call_args.args[0][1:3] == ["-m", "whub.webapp.runner"]

    def test_reuses_running_server(self, tmp_path):
        # ケース7
        dist_dir = _dist_dir(tmp_path)
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch("whub.commands.app.packaged_app_dist", return_value=dist_dir),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=9000),
            ),
            patch("whub.commands.app.subprocess.Popen") as mock_popen,
        ):
            result = CliRunner().invoke(app)

        assert result.exit_code == 0
        assert "app already running: http://127.0.0.1:9000" in result.output
        mock_popen.assert_not_called()

    def test_down_stops_managed_server(self, tmp_path):
        # ケース8
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8710),
            ),
            patch("whub.commands.app.os.getpgid", return_value=42),
            patch("whub.commands.app._is_running", return_value=False),
            patch("whub.commands.app.os.killpg") as mock_killpg,
            patch("whub.commands.app.time.sleep"),
            patch("whub.commands.app.remove_pid_record") as mock_remove,
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        assert "app stopped" in result.output
        mock_killpg.assert_called_once_with(42, signal.SIGTERM)
        mock_remove.assert_called_once_with(tmp_path / "app.pid", expected_pid=42)

    def test_down_escalates_to_sigkill(self, tmp_path):
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8712, mode="dev"),
            ),
            patch("whub.commands.app.os.getpgid", return_value=42),
            patch("whub.commands.app._is_running", return_value=True),
            patch("whub.commands.app.os.killpg") as mock_killpg,
            patch("whub.commands.app.time.monotonic", side_effect=[0, 1]),
            patch("whub.commands.app.time.sleep"),
            patch("whub.commands.app.remove_pid_record"),
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        assert mock_killpg.call_args_list == [
            call(42, signal.SIGTERM),
            call(42, signal.SIGKILL),
        ]

    def test_down_waits_for_graceful_exit(self, tmp_path):
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8710),
            ),
            patch("whub.commands.app.os.getpgid", return_value=42),
            patch("whub.commands.app._is_running", side_effect=[True, False, False]),
            patch("whub.commands.app.os.killpg") as mock_killpg,
            patch("whub.commands.app.time.monotonic", return_value=0),
            patch("whub.commands.app.time.sleep") as mock_sleep,
            patch("whub.commands.app.remove_pid_record"),
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        mock_killpg.assert_called_once_with(42, signal.SIGTERM)
        mock_sleep.assert_called_once_with(0.05)

    def test_down_reports_permission_error_without_removing_pid_record(self, tmp_path):
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8710),
            ),
            patch("whub.commands.app.os.getpgid", return_value=42),
            patch("whub.commands.app._is_running", return_value=True),
            patch(
                "whub.commands.app.os.killpg",
                side_effect=[None, PermissionError("denied")],
            ),
            patch("whub.commands.app.time.monotonic", side_effect=[0, 1]),
            patch("whub.commands.app.remove_pid_record") as mock_remove,
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 1
        assert "failed to stop app: denied" in result.output
        mock_remove.assert_not_called()

    def test_down_stops_only_the_app_in_its_own_process_group(self, tmp_path):
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8710),
            ),
            patch("whub.commands.app.os.getpgid", return_value=42),
            patch("whub.commands.app.os.getpgrp", return_value=42),
            patch("whub.commands.app.os.killpg") as mock_killpg,
            patch("whub.commands.app.os.kill") as mock_kill,
            patch("whub.commands.app._is_running", return_value=False),
            patch("whub.commands.app.remove_pid_record") as mock_remove,
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        assert "app stopped" in result.output
        mock_killpg.assert_not_called()
        mock_kill.assert_called_once_with(42, signal.SIGTERM)
        mock_remove.assert_called_once_with(tmp_path / "app.pid", expected_pid=42)

    def test_dev_starts_fixed_url(self, tmp_path):
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "package.json").write_text("{}")
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch("whub.commands.app.development_app_source", return_value=app_dir),
            patch("whub.commands.app._read_running_process", return_value=None),
            patch("whub.commands.app.subprocess.Popen") as mock_popen,
        ):
            result = CliRunner().invoke(app, ["dev"])

        assert result.exit_code == 0
        assert "app dev starting: http://127.0.0.1:8712" in result.output
        command = mock_popen.call_args.args[0]
        assert command[1:4] == ["-m", "whub.webapp.runner", "--dev"]
        assert "8712" in command
        assert "8713" in command
        assert mock_popen.call_args.kwargs == {
            "start_new_session": True,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }

    def test_dev_reuses_running_development_mode(self, tmp_path):
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8712, mode="dev"),
            ),
            patch("whub.commands.app.subprocess.Popen") as mock_popen,
        ):
            result = CliRunner().invoke(app, ["dev"])

        assert result.exit_code == 0
        assert "app dev already running: http://127.0.0.1:8712" in result.output
        mock_popen.assert_not_called()

    def test_down_dev_stops_only_development_server(self, tmp_path):
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8712, mode="dev"),
            ),
            patch("whub.commands.app.os.getpgid", return_value=42),
            patch("whub.commands.app._is_running", return_value=False),
            patch("whub.commands.app.os.killpg") as mock_killpg,
            patch("whub.commands.app.time.sleep"),
            patch("whub.commands.app.remove_pid_record") as mock_remove,
        ):
            result = CliRunner().invoke(app, ["down", "--dev"])

        assert result.exit_code == 0
        assert "app dev stopped" in result.output
        mock_killpg.assert_called_once_with(42, signal.SIGTERM)
        mock_remove.assert_called_once_with(tmp_path / "app-dev.pid", expected_pid=42)

    def test_down_skips_when_not_running(self, tmp_path):
        with (
            patch(
                "whub.commands.app.current_context",
                return_value=_app_context(tmp_path),
            ),
            patch("whub.commands.app._read_running_process", return_value=None),
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        assert "app not running" in result.output
