"""`whub boot`コマンドのCLI振る舞いテスト。

検証するケース:
1. localリソースへmerge/skills配布で"done"出力
2. リソース未存在でskip出力
3. workspace-hub自身への配布（_apply_workspace_boot）
4. boot=falseは_collect_boot_targetsで除外される
5. _merge_json：再帰マージ・リスト重複排除（ADR-0009例外：複雑分岐）
6. CodeGraph init失敗が後続ターゲットの配布を止めない（fail-safe）
7. wflow payload hashがcacheを除外し、内容変更を検出する
8. remote boot targetをhost単位で重複排除する
9. 同一hashのwflowは転送せず、差分時だけ安全に更新する
10. wflow install失敗を警告してbootを継続する

検証しないケース:
- 実際のrsync/SSH実行
- 実際のCodeGraph init実行
- boot assetsの具体的な内容（パッケージリソース依存）
- remote版codegraph fail-safe（localと共通のon_targets構造で代表検証）
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.boot import (
    boot,
    _collect_boot_targets,
    _collect_wflow_hosts,
    _copy_wflow_payload,
    _install_remote_wflow,
    _merge_json,
    _wflow_content_hash,
)
from whub.models import Manifest, SymlinkResource
from whub.tests.helpers import manifest


class TestBootSpec:
    def test_local_deploy(self, tmp_path):
        # ケース1
        m = manifest()
        local = m.resolve_project("local")
        local.resource.boot = True
        local.resource._resolved_workspace_path = tmp_path / "projects" / "local"
        local.resource._resolved_workspace_path.mkdir(parents=True)

        with (
            patch("whub.commands.boot.get_manifest", return_value=m),
            patch("whub.commands.boot._apply_workspace_boot"),
            patch("whub.commands.boot.shutil.which", return_value=None),
        ):
            result = CliRunner().invoke(boot, catch_exceptions=False)

        assert "done" in result.output
        assert "local" in result.output

    def test_skip_when_target_not_found(self, tmp_path):
        # ケース2
        m = manifest()
        local = m.resolve_project("local")
        local.resource.boot = True
        local.resource._resolved_workspace_path = tmp_path / "nonexistent"

        with (
            patch("whub.commands.boot.get_manifest", return_value=m),
            patch("whub.commands.boot._apply_workspace_boot"),
        ):
            result = CliRunner().invoke(boot, catch_exceptions=False)

        assert "skip" in result.output

    def test_workspace_boot_called(self):
        # ケース3
        m = manifest()
        with (
            patch("whub.commands.boot.get_manifest", return_value=m),
            patch("whub.commands.boot._apply_workspace_boot") as mock_ws,
        ):
            CliRunner().invoke(boot, catch_exceptions=False)

        mock_ws.assert_called_once()

    def test_collect_excludes_boot_false(self):
        # ケース4
        m = manifest()
        targets = _collect_boot_targets(m)

        assert all(t.resource.boot for t in targets)

    def test_codegraph_failure_does_not_stop_later_targets(self, tmp_path):
        # ケース8
        (tmp_path / "first").mkdir()
        (tmp_path / "second").mkdir()
        data = {
            "version": "2",
            "projects": [
                {
                    "name": "first",
                    "resource": {
                        "type": "symlink", "workspace_path": "first",
                        "source": str(tmp_path / "src1"), "boot": True,
                    },
                },
                {
                    "name": "second",
                    "resource": {
                        "type": "symlink", "workspace_path": "second",
                        "source": str(tmp_path / "src2"), "boot": True,
                    },
                },
            ],
        }
        m = Manifest.model_validate(data)
        m.projects[0].resource._resolved_workspace_path = tmp_path / "first"
        m.projects[1].resource._resolved_workspace_path = tmp_path / "second"

        with (
            patch("whub.commands.boot.get_manifest", return_value=m),
            patch("whub.commands.boot._apply_workspace_boot"),
            patch("whub.commands.boot._merged_files", side_effect=lambda *_: iter(())),
            patch("whub.commands.boot.shutil.copytree"),
            patch("whub.commands.boot.shutil.which", return_value="/bin/codegraph"),
            patch(
                "whub.commands.boot.subprocess.run",
                side_effect=[
                    subprocess.CalledProcessError(1, [], stderr="failed"),
                    subprocess.CompletedProcess([], 0),
                ],
            ),
        ):
            result = CliRunner().invoke(boot, catch_exceptions=False)

        assert result.exit_code == 0
        assert "first: CodeGraph init failed" in result.output
        assert "second (CodeGraph)" in result.output

    def test_collects_each_remote_boot_host_once(self):
        m = manifest()
        m.resolve_project("remote").resource.boot = True
        m.resolve_project("nested").resource.boot = True

        hosts = _collect_wflow_hosts(_collect_boot_targets(m))

        assert [name for name, _ in hosts] == ["home"]

    def test_boot_installs_wflow_once_per_remote_host(self):
        m = manifest()
        m.resolve_project("remote").resource.boot = True
        m.resolve_project("nested").resource.boot = True

        with (
            patch("whub.commands.boot.get_manifest", return_value=m),
            patch("whub.commands.boot._apply_workspace_boot"),
            patch("whub.commands.boot._install_remote_wflow") as install,
            patch("whub.commands.boot.on_targets"),
        ):
            result = CliRunner().invoke(boot, catch_exceptions=False)

        assert result.exit_code == 0
        install.assert_called_once_with("home", m.hosts["home"])


class TestWflowDeploySpec:
    def test_payload_runs_without_the_rest_of_whub(self, tmp_path):
        source = Path(__file__).parents[2] / "wflow"
        package_root = tmp_path / "src/whub"
        package_root.mkdir(parents=True)
        (package_root / "__init__.py").write_text("")
        _copy_wflow_payload(source, package_root / "wflow")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(tmp_path / "src")

        result = subprocess.run(
            [sys.executable, "-m", "whub.wflow", "--help"],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Manage declarative Workflows and task records." in result.stdout

    def test_content_hash_ignores_cache_and_detects_source_changes(self, tmp_path):
        source = _wflow_source(tmp_path)
        initial = _wflow_content_hash(source)
        cache = source / "__pycache__"
        cache.mkdir()
        (cache / "cli.pyc").write_bytes(b"cache")

        assert _wflow_content_hash(source) == initial

        (source / "cli.py").write_text("changed\n")
        assert _wflow_content_hash(source) != initial

    def test_skips_transfer_when_installed_hash_matches(self, tmp_path, capsys):
        source = _wflow_source(tmp_path)
        content_hash = _wflow_content_hash(source)
        with (
            patch("whub.commands.boot._wflow_assets", return_value=source),
            patch(
                "whub.commands.boot._remote_wflow_state",
                return_value=("/home/test/.local/share/wflow", "/home/test/.local/bin", content_hash),
            ),
            patch("whub.commands.boot.run_ssh_command") as ssh,
            patch("whub.commands.boot.run_rsync_command") as rsync,
        ):
            _install_remote_wflow("home", manifest().hosts["home"])

        ssh.assert_not_called()
        rsync.assert_not_called()
        assert "skip    home (wflow unchanged)" in capsys.readouterr().out

    def test_installs_changed_payload_through_staging(self, tmp_path, capsys):
        source = _wflow_source(tmp_path)

        def rsync(host, local_src, remote_dest, **kwargs):
            del host, kwargs
            payload = Path(local_src)
            assert (payload / "__main__.py").is_file()
            assert (payload / "requirements.txt").is_file()
            assert "__pycache__" not in {part for path in payload.rglob("*") for part in path.parts}
            assert remote_dest.endswith("/src/whub/wflow")
            return subprocess.CompletedProcess([], 0)

        with (
            patch("whub.commands.boot._wflow_assets", return_value=source),
            patch(
                "whub.commands.boot._remote_wflow_state",
                return_value=("/home/test/.local/share/wflow", "/home/test/.local/bin", None),
            ),
            patch(
                "whub.commands.boot.run_ssh_command",
                return_value=subprocess.CompletedProcess([], 0, stdout=""),
            ) as ssh,
            patch("whub.commands.boot.run_rsync_command", side_effect=rsync),
            patch("whub.commands.boot.secrets.token_hex", return_value="version"),
        ):
            _install_remote_wflow("home", manifest().hosts["home"])

        assert ssh.call_count == 2
        install_command = ssh.call_args_list[-1].args[1]
        assert "python3 -m venv" in install_command
        assert "mv -Tf" in install_command
        assert ssh.call_args_list[-1].kwargs["input"].startswith("#!/bin/sh")
        assert "done    home (wflow)" in capsys.readouterr().out

    def test_warns_when_install_fails(self, tmp_path, capsys):
        source = _wflow_source(tmp_path)
        with (
            patch("whub.commands.boot._wflow_assets", return_value=source),
            patch(
                "whub.commands.boot._remote_wflow_state",
                side_effect=OSError("offline"),
            ),
        ):
            _install_remote_wflow("home", manifest().hosts["home"])

        assert "WARN    home: wflow install failed: offline" in capsys.readouterr().out


class TestMergeJsonSpec:
    def test_recursive_merge(self):
        # ケース6a
        overlay = '{"a": {"x": 1}, "b": 2}'
        existing = '{"a": {"y": 2}, "c": 3}'
        result = _merge_json(overlay, existing)

        import json
        data = json.loads(result)
        assert data["a"] == {"x": 1, "y": 2}
        assert data["b"] == 2
        assert data["c"] == 3

    def test_list_deduplication(self):
        # ケース6b
        overlay = '{"items": [1, 2, 3]}'
        existing = '{"items": [2, 3, 4]}'
        result = _merge_json(overlay, existing)

        import json
        data = json.loads(result)
        assert data["items"] == [2, 3, 4, 1]


def _wflow_source(root: Path) -> Path:
    source = root / "wflow"
    source.mkdir()
    (source / "__init__.py").write_text("")
    (source / "__main__.py").write_text("from whub.wflow.cli import main\nmain()\n")
    (source / "cli.py").write_text("def main(): pass\n")
    (source / "requirements.txt").write_text("click>=8.1\n")
    return source
