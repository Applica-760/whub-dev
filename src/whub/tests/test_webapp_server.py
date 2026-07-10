"""S1 web application server tests.

検証するケース:
1. health APIが正常応答を返す
2. dist配下の静的ファイルを返す
3. 非APIの未マッチパスはSPAフォールバックする
4. 未定義のAPIパスはSPAフォールバックしない
5. dist欠如時にビルド手順を案内する
6. デフォルトでブラウザを開く
7. --no-openでブラウザを開かない
8. ブラウザ起動失敗がサーバー起動を妨げない
9. --portでポートを変更できる
10. app_dist_pathがWHUB_ROOT配下のdistを返す

検証しないケース:
- 実際のuvicornサーバー起動とブラウザ起動
"""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner
from fastapi.testclient import TestClient

from whub.commands.app import app
from whub.paths import app_dist_path
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

        response = client.get("/api/todos")

        assert response.status_code == 404


class TestAppCommand:
    def test_missing_dist_shows_build_instruction(self, tmp_path):
        # ケース5
        with patch("whub.commands.app.app_dist_path", return_value=tmp_path / "dist"):
            result = CliRunner().invoke(app)

        assert result.exit_code != 0
        assert "cd app && npm install && npm run build" in result.output

    def test_opens_browser_and_uses_requested_port(self, tmp_path):
        # ケース6,9
        dist_dir = _dist_dir(tmp_path)
        with (
            patch("whub.commands.app.app_dist_path", return_value=dist_dir),
            patch("whub.commands.app.webbrowser.open") as mock_open,
            patch("whub.commands.app.uvicorn.run") as mock_run,
        ):
            result = CliRunner().invoke(app, ["--port", "9000"])

        assert result.exit_code == 0
        mock_open.assert_called_once_with("http://127.0.0.1:9000")
        assert mock_run.call_args.kwargs == {"host": "127.0.0.1", "port": 9000}

    def test_no_open_skips_browser(self, tmp_path):
        # ケース7
        dist_dir = _dist_dir(tmp_path)
        with (
            patch("whub.commands.app.app_dist_path", return_value=dist_dir),
            patch("whub.commands.app.webbrowser.open") as mock_open,
            patch("whub.commands.app.uvicorn.run"),
        ):
            result = CliRunner().invoke(app, ["--no-open"])

        assert result.exit_code == 0
        mock_open.assert_not_called()

    def test_browser_failure_does_not_stop_server(self, tmp_path):
        # ケース8
        dist_dir = _dist_dir(tmp_path)
        with (
            patch("whub.commands.app.app_dist_path", return_value=dist_dir),
            patch(
                "whub.commands.app.webbrowser.open",
                side_effect=RuntimeError("browser unavailable"),
            ),
            patch("whub.commands.app.uvicorn.run") as mock_run,
        ):
            result = CliRunner().invoke(app)

        assert result.exit_code == 0
        mock_run.assert_called_once()
