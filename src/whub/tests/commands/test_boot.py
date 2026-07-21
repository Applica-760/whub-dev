"""`whub boot`コマンドのCLI振る舞いテスト。

検証するケース:
1. localリソースへmerge/skills配布で"done"出力
2. リソース未存在でskip出力
3. workspace-hub自身への配布（_apply_workspace_boot）
4. boot=falseは_collect_boot_targetsで除外される
5. _merge_json：再帰マージ・リスト重複排除（ADR-0009例外：複雑分岐）
6. CodeGraph init失敗が後続ターゲットの配布を止めない（fail-safe）
7. remote boot targetへwflow CLIを頒布しない

検証しないケース:
- 実際のrsync/SSH実行
- 実際のCodeGraph init実行
- boot assetsの具体的な内容（パッケージリソース依存）
- remote版codegraph fail-safe（localと共通のon_targets構造で代表検証）
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.boot import (
    boot,
    _collect_boot_targets,
    _merge_json,
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
                        "type": "symlink",
                        "workspace_path": "first",
                        "source": str(tmp_path / "src1"),
                        "boot": True,
                    },
                },
                {
                    "name": "second",
                    "resource": {
                        "type": "symlink",
                        "workspace_path": "second",
                        "source": str(tmp_path / "src2"),
                        "boot": True,
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

    def test_boot_does_not_install_a_remote_cli(self):
        m = manifest()
        m.resolve_project("remote").resource.boot = True
        m.resolve_project("nested").resource.boot = True

        with (
            patch("whub.commands.boot.get_manifest", return_value=m),
            patch("whub.commands.boot._apply_workspace_boot"),
            patch("whub.commands.boot.on_targets"),
            patch("whub.commands.boot.run_ssh_command") as ssh,
        ):
            result = CliRunner().invoke(boot, catch_exceptions=False)

        assert result.exit_code == 0
        ssh.assert_not_called()


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
