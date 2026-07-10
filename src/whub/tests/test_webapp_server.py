"""S1 web application server tests.

検証するケース:
1. health APIが正常応答を返す
2. dist配下の静的ファイルを返す
3. 非APIの未マッチパスはSPAフォールバックする
4. 未定義のAPIパスはSPAフォールバックしない
5. dist欠如時にビルド手順を案内する
6. 常駐子プロセスを指定portで起動する
7. 起動済みサーバーを再利用する
8. downが管理PIDを停止する
9. downが必要に応じてSIGKILLへ昇格する
10. downが未起動時に成功する
11. app_pid_pathがWHUB_ROOT配下のPIDファイルを返す

検証しないケース:
- 実際の常駐プロセス起動・停止（統合確認で検証）
"""
from __future__ import annotations

import signal
from unittest.mock import call, patch

from click.testing import CliRunner
from fastapi.testclient import TestClient

from whub.commands.app import app
from whub.paths import app_dist_path, app_pid_path
from whub.webapp.runner import AppProcessRecord
from whub.webapp.server import create_app


def _dist_dir(tmp_path):
    dist_dir = tmp_path / "dist"
    (dist_dir / "assets").mkdir(parents=True)
    (dist_dir / "index.html").write_text("<main>whub</main>")
    (dist_dir / "assets" / "app.js").write_text("console.log('whub')")
    return dist_dir


class TestWebappServer:
    def test_app_dist_path_uses_whub_root(self, tmp_path, monkeypatch):
        # ケース10
        monkeypatch.setenv("WHUB_ROOT", str(tmp_path))

        assert app_dist_path() == tmp_path / "app" / "dist"
        assert app_pid_path() == tmp_path / ".whub" / "app.pid"

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
    def test_missing_dist_shows_build_instruction(self, tmp_path):
        # ケース5
        with patch("whub.commands.app.app_dist_path", return_value=tmp_path / "dist"):
            result = CliRunner().invoke(app)

        assert result.exit_code != 0
        assert "cd app && npm install && npm run build" in result.output

    def test_starts_detached_server_with_requested_port(self, tmp_path):
        # ケース6,9
        dist_dir = _dist_dir(tmp_path)
        with (
            patch("whub.commands.app.app_dist_path", return_value=dist_dir),
            patch("whub.commands.app.app_pid_path", return_value=tmp_path / "app.pid"),
            patch("whub.commands.app._read_running_process", return_value=None),
            patch("whub.commands.app.subprocess.Popen") as mock_popen,
        ):
            result = CliRunner().invoke(app, ["--port", "9000"])

        assert result.exit_code == 0
        assert "app starting: http://127.0.0.1:9000" in result.output
        assert mock_popen.call_args.kwargs == {"start_new_session": True}
        assert mock_popen.call_args.args[0][1:3] == ["-m", "whub.webapp.runner"]

    def test_reuses_running_server(self, tmp_path):
        # ケース7
        dist_dir = _dist_dir(tmp_path)
        with (
            patch("whub.commands.app.app_dist_path", return_value=dist_dir),
            patch("whub.commands.app.app_pid_path", return_value=tmp_path / "app.pid"),
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
            patch("whub.commands.app.app_pid_path", return_value=tmp_path / "app.pid"),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8710),
            ),
            patch("whub.commands.app._is_running", return_value=False),
            patch("whub.commands.app.os.kill") as mock_kill,
            patch("whub.commands.app.time.sleep"),
            patch("whub.commands.app.remove_pid_record") as mock_remove,
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        assert "app stopped" in result.output
        mock_kill.assert_called_once_with(42, signal.SIGTERM)
        mock_remove.assert_called_once_with(tmp_path / "app.pid", expected_pid=42)

    def test_down_escalates_to_sigkill(self, tmp_path):
        with (
            patch("whub.commands.app.app_pid_path", return_value=tmp_path / "app.pid"),
            patch(
                "whub.commands.app._read_running_process",
                return_value=AppProcessRecord(pid=42, port=8710),
            ),
            patch("whub.commands.app._is_running", return_value=True),
            patch("whub.commands.app.os.kill") as mock_kill,
            patch("whub.commands.app.time.sleep"),
            patch("whub.commands.app.remove_pid_record"),
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        assert mock_kill.call_args_list == [
            call(42, signal.SIGTERM),
            call(42, signal.SIGKILL),
        ]

    def test_down_skips_when_not_running(self, tmp_path):
        with (
            patch("whub.commands.app.app_pid_path", return_value=tmp_path / "app.pid"),
            patch("whub.commands.app._read_running_process", return_value=None),
        ):
            result = CliRunner().invoke(app, ["down"])

        assert result.exit_code == 0
        assert "app not running" in result.output
