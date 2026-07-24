"""`whub mount`/`whub unmount`コマンドのCLI振る舞いテスト。

検証するケース:
1. 正常系mount：sshfsコマンドで呼ばれ"mount"出力
2. 既mounted → skip
3. stale → エラー表示
4. sshfs未インストール → エラー
5. 名指し → mount=falseでもmount実行
6. -a → mount=false含む
7. unmount正常系：umountコマンド実行で"unmount"出力
8. mount失敗時、作成したmountpointはrmdirされる（副作用境界）
9. mount失敗時、既存のmountpointは保持される（副作用境界）
10. stale mountはsshfsを起動せず、force unmountで解除する
11. slow（健全だが高遅延）はprecheckでskipし再mountしない
12. post-mount probeがslowでもmount成功扱いとしcleanupしない

検証しないケース:
- 実際のsshfs/umount/diskutil実行
- fuse-tのmount table遅延（sleep付きリトライ）
"""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from whub.commands.mount import (
    _mount_one,
    _select_targets,
    mount,
    unmount,
)
from whub.core.health import ResourceHealth
from whub.tests.helpers import manifest


@pytest.fixture(autouse=True)
def _disable_mount_log():
    with patch("whub.commands.mount.write_mount_log"):
        yield


class TestMountSpec:
    def test_mounts_remote_resource(self, tmp_path):
        # ケース1
        m = manifest()
        remote = m.resolve_project("remote").resource
        remote._resolved_workspace_path = tmp_path / "projects" / "remote"
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        health_seq = [ResourceHealth("unmounted"), ResourceHealth("ok")]
        with (
            patch("whub.commands.mount.get_manifest", return_value=m),
            patch("whub.commands.mount.inspect_mount", side_effect=health_seq),
            patch("whub.commands.mount.subprocess.run", mock_run),
            patch(
                "whub.commands.mount.shutil.which", return_value="/usr/local/bin/sshfs"
            ),
        ):
            result = CliRunner().invoke(mount, ["remote"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "mount" in result.output

    def test_skips_when_already_mounted(self):
        # ケース2
        m = manifest()
        with (
            patch("whub.commands.mount.get_manifest", return_value=m),
            patch(
                "whub.commands.mount.inspect_mount", return_value=ResourceHealth("ok")
            ),
            patch(
                "whub.commands.mount.shutil.which", return_value="/usr/local/bin/sshfs"
            ),
        ):
            result = CliRunner().invoke(mount, ["remote"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "skip" in result.output

    def test_stale_shows_error(self):
        # ケース3
        m = manifest()
        mock_run = MagicMock()
        with (
            patch("whub.commands.mount.get_manifest", return_value=m),
            patch(
                "whub.commands.mount.inspect_mount",
                return_value=ResourceHealth("stale"),
            ),
            patch(
                "whub.commands.mount.shutil.which", return_value="/usr/local/bin/sshfs"
            ),
            patch("whub.commands.mount.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(mount, ["remote"])

        assert result.exit_code != 0
        assert "STALE" in result.output
        mock_run.assert_not_called()

    def test_sshfs_not_found_errors(self):
        # ケース4
        with (
            patch("whub.commands.mount.shutil.which", return_value=None),
        ):
            result = CliRunner().invoke(mount)

        assert result.exit_code != 0
        assert "sshfs not found" in result.output

    def test_select_targets_by_name_ignores_mount_flag(self):
        # ケース5
        m = manifest()
        targets = _select_targets(m, "nested")

        assert len(targets) == 1
        assert targets[0][0].name == "nested"

    def test_select_targets_all_includes_mount_false(self):
        # ケース6
        m = manifest()
        targets_auto = _select_targets(m, None, auto_only=True)
        targets_all = _select_targets(m, None, auto_only=False)

        assert len(targets_all) > len(targets_auto)
        names_all = {t[0].name for t in targets_all}
        assert "nested" in names_all

    def test_unmounts_remote_resource(self):
        # ケース7
        m = manifest()
        health_seq = [ResourceHealth("ok"), ResourceHealth("unmounted")]
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.commands.mount.get_manifest", return_value=m),
            patch("whub.commands.mount.inspect_mount", side_effect=health_seq),
            patch("whub.commands.mount.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(unmount, ["remote"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "unmount" in result.output

    def test_force_unmounts_stale_resource(self):
        # ケース10
        m = manifest()
        remote = m.resolve_project("remote").resource
        health_seq = [ResourceHealth("stale"), ResourceHealth("unmounted")]
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.commands.mount.get_manifest", return_value=m),
            patch("whub.commands.mount.inspect_mount", side_effect=health_seq),
            patch("whub.commands.mount.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(
                unmount, ["remote", "--force"], catch_exceptions=False
            )

        assert result.exit_code == 0
        assert "unmount" in result.output
        mock_run.assert_called_once_with(
            ["umount", "-f", str(remote._resolved_workspace_path)],
            capture_output=True,
            text=True,
        )

    def test_mount_failure_removes_created_mountpoint(self, tmp_path):
        # ケース8
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        mountpoint = tmp_path / "mnt"
        resource._resolved_workspace_path = mountpoint
        with (
            patch(
                "whub.commands.mount.inspect_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.commands.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.commands.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", "failed"),
            ),
        ):
            status = _mount_one(project, resource)

        assert status == "FAIL: failed"
        assert not mountpoint.exists()

    def test_mount_failure_keeps_existing_mountpoint(self, tmp_path):
        # ケース9
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        mountpoint = tmp_path / "mnt"
        mountpoint.mkdir()
        resource._resolved_workspace_path = mountpoint
        with (
            patch(
                "whub.commands.mount.inspect_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.commands.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.commands.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", "failed"),
            ),
        ):
            status = _mount_one(project, resource)

        assert status == "FAIL: failed"
        assert mountpoint.exists()

    def test_mount_readability_failure_unmounts_and_reports(self, tmp_path):
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        mountpoint = tmp_path / "mnt"
        resource._resolved_workspace_path = mountpoint
        health_seq = [
            ResourceHealth("unmounted"),
            ResourceHealth(
                "unreadable",
                "Operation not permitted",
                "allow Network Volumes access, then remount",
            ),
        ]
        with (
            patch("whub.commands.mount.inspect_mount", side_effect=health_seq),
            patch("whub.commands.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.commands.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
            patch(
                "whub.commands.mount._unmount_one", return_value="unmount"
            ) as cleanup,
        ):
            status = _mount_one(project, resource)

        assert status == (
            "FAIL: mount unreadable: Operation not permitted; cleanup=unmount; "
            "recovery: allow Network Volumes access, then remount"
        )
        cleanup.assert_called_once_with(project, resource, force=True)
        assert not mountpoint.exists()

    def test_skips_when_mounted_but_slow(self):
        # ケース11
        m = manifest()
        mock_run = MagicMock()
        with (
            patch("whub.commands.mount.get_manifest", return_value=m),
            patch(
                "whub.commands.mount.inspect_mount",
                return_value=ResourceHealth("slow", "directory listing exceeded 3s"),
            ),
            patch(
                "whub.commands.mount.shutil.which", return_value="/usr/local/bin/sshfs"
            ),
            patch("whub.commands.mount.subprocess.run", mock_run),
        ):
            result = CliRunner().invoke(mount, ["remote"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "skip" in result.output
        mock_run.assert_not_called()

    def test_slow_post_mount_probe_succeeds_without_cleanup(self, tmp_path):
        # ケース12
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_workspace_path = tmp_path / "mnt"
        health_seq = [
            ResourceHealth("unmounted"),
            ResourceHealth("slow", "directory listing exceeded 3s"),
        ]
        with (
            patch("whub.commands.mount.inspect_mount", side_effect=health_seq),
            patch("whub.commands.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.commands.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
            patch("whub.commands.mount._unmount_one") as cleanup,
        ):
            status = _mount_one(project, resource)

        assert status == "mount"
        cleanup.assert_not_called()

    def test_sshfs_stderr_is_not_persisted(self, tmp_path):
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_workspace_path = tmp_path / "mnt"
        secret = "user@host:/private/path IdentityFile=/Users/private/key"
        with (
            patch(
                "whub.commands.mount.inspect_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.commands.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.commands.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", secret),
            ),
            patch("whub.commands.mount.write_mount_log") as write_log,
        ):
            _mount_one(project, resource)

        sshfs_record = next(
            call.kwargs
            for call in write_log.call_args_list
            if call.kwargs["stage"] == "sshfs"
        )
        assert sshfs_record["detail"] == "sshfs command failed"
        assert secret not in repr(sshfs_record)
