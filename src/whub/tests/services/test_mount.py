"""mount serviceのオーケストレーション仕様テスト。

検証するケース:
1. shared host mountはhostごとに1回のsshfsで行い、workspace pathをsymlinkにする
2. 健全なhost mountでは誤ったworkspace symlinkを修復してskipを返す
3. 個別mount（mount_root未定義host）の正常系
4. 既mounted → skip
5. stale → sshfsを起動せずSTALEを返す
6. sshfs未インストール → ServiceError
7. 名指し → mount=falseでもmount対象になる
8. -a相当 → mount=false含む
9. 個別unmountの正常系
10. shared hostは一度だけunmountし、workspace symlinkを残す
11. mount失敗時、作成したmountpointはrmdirされる（副作用境界）
12. mount失敗時、既存のmountpointは保持される（副作用境界）
13. post-mount probeがunreadableならcleanupして報告する
14. slow（健全だが高遅延）はprecheckでskipし再mountしない
15. post-mount probeがslowでもmount成功扱いとしcleanupしない
16. sshfs stderrはmount logへ永続化しない
17. host識別子はpath componentとして安全化される

検証しないケース:
- 実際のsshfs/umount/diskutil実行
- fuse-tのmount table遅延（sleep付きリトライ）
"""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from whub.core.context import WhubContext
from whub.core.health import ResourceHealth
from whub.services.errors import ServiceError
from whub.services.mount import (
    _mount_host,
    _mount_one,
    host_mount_id,
    host_mountpoint,
    host_volume_name,
    mount_targets,
    select_targets,
    unmount_targets,
)
from whub.tests.helpers import manifest


@pytest.fixture(autouse=True)
def _disable_mount_log():
    with patch("whub.services.mount.write_mount_log"):
        yield


@pytest.fixture
def _sshfs_installed():
    with patch("whub.services.mount.shutil.which", return_value="/usr/bin/sshfs"):
        yield


def _statuses(results) -> list[str]:
    return [item.status for item in results]


class TestHostIdentifiers:
    def test_host_mount_id_is_a_safe_path_component(self) -> None:
        # ケース17
        host_name = "../../outside"

        assert host_mount_id(host_name) == "host-..%2F..%2Foutside"
        assert host_volume_name(host_name) == "whub-host-..%2F..%2Foutside"

    def test_host_mountpoint_stays_under_runtime_mounts(self, tmp_path) -> None:
        context = WhubContext(tmp_path)
        with patch("whub.services.mount.current_context", return_value=context):
            mountpoint = host_mountpoint("../../outside")

        assert mountpoint == (
            Path(tmp_path) / "runtime" / "mounts" / "host-..%2F..%2Foutside"
        )


class TestMountSpec:
    def test_mounts_host_once_and_links_workspace_paths(
        self, tmp_path, _sshfs_installed
    ):
        # ケース1
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_host.mount_root = "/srv"
        resource._resolved_workspace_path = tmp_path / "workspace" / "remote"
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        with (
            patch(
                "whub.services.mount.inspect_host_mount",
                side_effect=[ResourceHealth("unmounted"), ResourceHealth("ok")],
            ),
            patch("whub.services.mount.host_mountpoint", return_value=mountpoint),
            patch(
                "whub.services.mount.build_sshfs_command",
                return_value=["sshfs"],
            ) as build,
            patch(
                "whub.services.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
        ):
            results = mount_targets(m, "remote")

        assert _statuses(results) == ["mount"]
        assert resource._resolved_workspace_path.readlink() == mountpoint / "remote"
        assert build.call_args.args[1] == "/srv"

    def test_repairs_wrong_workspace_symlink_for_healthy_host(self, tmp_path):
        # ケース2
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_host.mount_root = "/srv"
        resource._resolved_workspace_path = tmp_path / "workspace" / "remote"
        resource._resolved_workspace_path.parent.mkdir(parents=True)
        resource._resolved_workspace_path.symlink_to(tmp_path / "wrong")
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        with (
            patch(
                "whub.services.mount.inspect_host_mount",
                return_value=ResourceHealth("ok"),
            ),
            patch("whub.services.mount.host_mountpoint", return_value=mountpoint),
        ):
            status = _mount_host("home", [(project, resource)])

        assert status == "skip"
        assert resource._resolved_workspace_path.readlink() == mountpoint / "remote"

    def test_mounts_remote_resource(self, tmp_path, _sshfs_installed):
        # ケース3
        m = manifest()
        remote = m.resolve_project("remote").resource
        remote._resolved_workspace_path = tmp_path / "projects" / "remote"
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        health_seq = [ResourceHealth("unmounted"), ResourceHealth("ok")]
        with (
            patch("whub.services.mount.inspect_mount", side_effect=health_seq),
            patch("whub.services.mount.subprocess.run", mock_run),
        ):
            results = mount_targets(m, "remote")

        assert _statuses(results) == ["mount"]

    def test_skips_when_already_mounted(self, _sshfs_installed):
        # ケース4
        m = manifest()
        with patch(
            "whub.services.mount.inspect_mount", return_value=ResourceHealth("ok")
        ):
            results = mount_targets(m, "remote")

        assert _statuses(results) == ["skip"]

    def test_stale_is_reported_without_mounting(self, _sshfs_installed):
        # ケース5
        m = manifest()
        mock_run = MagicMock()
        with (
            patch(
                "whub.services.mount.inspect_mount",
                return_value=ResourceHealth("stale"),
            ),
            patch("whub.services.mount.subprocess.run", mock_run),
        ):
            results = mount_targets(m, "remote")

        assert results[0].status.startswith("STALE")
        assert not results[0].ok
        mock_run.assert_not_called()

    def test_sshfs_not_found_errors(self):
        # ケース6
        m = manifest()
        with patch("whub.services.mount.shutil.which", return_value=None):
            with pytest.raises(ServiceError, match="sshfs not found"):
                mount_targets(m, None)

    def test_select_targets_by_name_ignores_mount_flag(self):
        # ケース7
        m = manifest()
        targets = select_targets(m, "nested")

        assert len(targets) == 1
        assert targets[0][0].name == "nested"

    def test_select_targets_all_includes_mount_false(self):
        # ケース8
        m = manifest()
        targets_auto = select_targets(m, None, auto_only=True)
        targets_all = select_targets(m, None, auto_only=False)

        assert len(targets_all) > len(targets_auto)
        names_all = {t[0].name for t in targets_all}
        assert "nested" in names_all

    def test_select_targets_rejects_unknown_project(self):
        m = manifest()
        with pytest.raises(ServiceError, match="unknown project"):
            select_targets(m, "no-such-project")

    def test_unmounts_remote_resource(self):
        # ケース9
        m = manifest()
        m.projects = [project for project in m.projects if project.name != "nested"]
        health_seq = [ResourceHealth("ok"), ResourceHealth("unmounted")]
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.services.mount.inspect_mount", side_effect=health_seq),
            patch("whub.services.mount.subprocess.run", mock_run),
        ):
            results = unmount_targets(m)

        assert _statuses(results) == ["unmount"]

    def test_unmounts_shared_host_once_and_keeps_workspace_symlink(self, tmp_path):
        # ケース10
        m = manifest()
        m.projects = [project for project in m.projects if project.name != "nested"]
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_host.mount_root = "/srv"
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        mountpoint.mkdir(parents=True)
        resource._resolved_workspace_path = tmp_path / "workspace" / "remote"
        resource._resolved_workspace_path.parent.mkdir(parents=True)
        resource._resolved_workspace_path.symlink_to(mountpoint / "remote")
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch(
                "whub.services.mount.inspect_host_mount",
                side_effect=[ResourceHealth("ok"), ResourceHealth("unmounted")],
            ),
            patch("whub.services.mount.host_mountpoint", return_value=mountpoint),
            patch("whub.services.mount.subprocess.run", mock_run),
        ):
            results = unmount_targets(m)

        assert _statuses(results) == ["unmount"]
        mock_run.assert_called_once_with(
            ["umount", str(mountpoint)],
            capture_output=True,
            text=True,
        )
        assert resource._resolved_workspace_path.is_symlink()
        assert not mountpoint.exists()

    def test_force_unmounts_stale_resource(self):
        m = manifest()
        m.projects = [project for project in m.projects if project.name != "nested"]
        remote = m.resolve_project("remote").resource
        health_seq = [ResourceHealth("stale"), ResourceHealth("unmounted")]
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch("whub.services.mount.inspect_mount", side_effect=health_seq),
            patch("whub.services.mount.subprocess.run", mock_run),
        ):
            results = unmount_targets(m, force=True)

        assert _statuses(results) == ["unmount"]
        mock_run.assert_called_once_with(
            ["umount", "-f", str(remote._resolved_workspace_path)],
            capture_output=True,
            text=True,
        )

    def test_mount_failure_removes_created_mountpoint(self, tmp_path):
        # ケース11
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        mountpoint = tmp_path / "mnt"
        resource._resolved_workspace_path = mountpoint
        with (
            patch(
                "whub.services.mount.inspect_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.services.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", "failed"),
            ),
        ):
            status = _mount_one(project, resource)

        assert status == "FAIL: failed"
        assert not mountpoint.exists()

    def test_mount_failure_keeps_existing_mountpoint(self, tmp_path):
        # ケース12
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        mountpoint = tmp_path / "mnt"
        mountpoint.mkdir()
        resource._resolved_workspace_path = mountpoint
        with (
            patch(
                "whub.services.mount.inspect_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.services.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", "failed"),
            ),
        ):
            status = _mount_one(project, resource)

        assert status == "FAIL: failed"
        assert mountpoint.exists()

    def test_mount_readability_failure_unmounts_and_reports(self, tmp_path):
        # ケース13
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
            patch("whub.services.mount.inspect_mount", side_effect=health_seq),
            patch("whub.services.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
            patch(
                "whub.services.mount._unmount_one", return_value="unmount"
            ) as cleanup,
        ):
            status = _mount_one(project, resource)

        assert status == (
            "FAIL: mount unreadable: Operation not permitted; cleanup=unmount; "
            "recovery: allow Network Volumes access, then remount"
        )
        cleanup.assert_called_once_with(project, resource, force=True)
        assert not mountpoint.exists()

    def test_skips_when_mounted_but_slow(self, _sshfs_installed):
        # ケース14
        m = manifest()
        mock_run = MagicMock()
        with (
            patch(
                "whub.services.mount.inspect_mount",
                return_value=ResourceHealth("slow", "directory listing exceeded 3s"),
            ),
            patch("whub.services.mount.subprocess.run", mock_run),
        ):
            results = mount_targets(m, "remote")

        assert _statuses(results) == ["skip"]
        mock_run.assert_not_called()

    def test_slow_post_mount_probe_succeeds_without_cleanup(self, tmp_path):
        # ケース15
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_workspace_path = tmp_path / "mnt"
        health_seq = [
            ResourceHealth("unmounted"),
            ResourceHealth("slow", "directory listing exceeded 3s"),
        ]
        with (
            patch("whub.services.mount.inspect_mount", side_effect=health_seq),
            patch("whub.services.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
            patch("whub.services.mount._unmount_one") as cleanup,
        ):
            status = _mount_one(project, resource)

        assert status == "mount"
        cleanup.assert_not_called()

    def test_sshfs_stderr_is_not_persisted(self, tmp_path):
        # ケース16
        m = manifest()
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_workspace_path = tmp_path / "mnt"
        secret = "user@host:/private/path IdentityFile=/Users/private/key"
        with (
            patch(
                "whub.services.mount.inspect_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.services.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", secret),
            ),
            patch("whub.services.mount.write_mount_log") as write_log,
        ):
            _mount_one(project, resource)

        sshfs_record = next(
            call.kwargs
            for call in write_log.call_args_list
            if call.kwargs["stage"] == "sshfs"
        )
        assert sshfs_record["detail"] == "sshfs command failed"
        assert secret not in repr(sshfs_record)
