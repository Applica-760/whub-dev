"""`whub init`コマンドのCLI振る舞いテスト。

検証するケース:
1. 正常系：data_dir存在・manifest.yaml存在でconfig.toml作成
2. 同内容skip：既存config.tomlと同一内容で"skip"出力
3. data_dir未存在 → エラー
4. data_dirがファイル → エラー
5. manifest.yaml未存在 → エラー
6. 既存config.toml + --forceなし → エラー
7. 既存config.toml + --force → 上書き

検証しないケース:
- .whubがシンボリックリンクの場合（実環境固有）
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from whub.commands.init import init


@pytest.fixture()
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "manifest.yaml").write_text("version: '2'\nprojects: []\n")
    return d


@pytest.fixture()
def config_env(tmp_path, monkeypatch):
    config_dir = tmp_path / ".whub"
    config_path = config_dir / "config.toml"
    monkeypatch.setattr("whub.commands.init.whub_config_dir", lambda: config_dir)
    monkeypatch.setattr("whub.commands.init.whub_config_path", lambda: config_path)
    return config_dir, config_path


class TestInitSpec:
    def test_creates_config(self, data_dir, config_env):
        # ケース1
        _, config_path = config_env
        result = CliRunner().invoke(init, [str(data_dir)])

        assert result.exit_code == 0
        assert "init" in result.output
        assert config_path.exists()
        assert json.dumps(str(data_dir.resolve())) in config_path.read_text()

    def test_skips_when_same_content(self, data_dir, config_env):
        # ケース2
        config_dir, config_path = config_env
        config_dir.mkdir(parents=True, exist_ok=True)
        content = f"data_dir = {json.dumps(str(data_dir.resolve()))}\n"
        config_path.write_text(content)

        result = CliRunner().invoke(init, [str(data_dir)])

        assert result.exit_code == 0
        assert "skip" in result.output

    def test_rejects_nonexistent_data_dir(self, tmp_path, config_env):
        # ケース3
        result = CliRunner().invoke(init, [str(tmp_path / "missing")])

        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_rejects_file_as_data_dir(self, tmp_path, config_env):
        # ケース4
        f = tmp_path / "afile"
        f.write_text("x")

        result = CliRunner().invoke(init, [str(f)])

        assert result.exit_code != 0
        assert "not a directory" in result.output

    def test_rejects_data_dir_without_manifest(self, tmp_path, config_env):
        # ケース5
        d = tmp_path / "empty"
        d.mkdir()

        result = CliRunner().invoke(init, [str(d)])

        assert result.exit_code != 0
        assert "manifest.yaml not found" in result.output

    def test_rejects_existing_config_without_force(self, data_dir, config_env):
        # ケース6
        config_dir, config_path = config_env
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text("data_dir = \"/old\"\n")

        result = CliRunner().invoke(init, [str(data_dir)])

        assert result.exit_code != 0
        assert "--force" in result.output

    def test_overwrites_existing_config_with_force(self, data_dir, config_env):
        # ケース7
        config_dir, config_path = config_env
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text("data_dir = \"/old\"\n")

        result = CliRunner().invoke(init, [str(data_dir), "--force"])

        assert result.exit_code == 0
        assert "init" in result.output
        assert json.dumps(str(data_dir.resolve())) in config_path.read_text()
