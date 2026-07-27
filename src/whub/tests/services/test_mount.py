"""mount serviceのオーケストレーション仕様テスト。

検証するケース:
1. hostごとに1回だけsshfsし、対象resourceのworkspace pathをmount内へのsymlinkにする
2. 同一hostの複数resourceでもsshfsは1回、symlinkはresource数だけ作る
3. 健全なhost mountでは誤ったworkspace symlinkを修復してskipを返す
4. workspace pathが通常ファイル/ディレクトリなら上書きせず失敗する
5. 既mounted → skip
6. stale → sshfsを起動せずSTALEを返す
7. sshfs未インストール → ServiceError
8. 名指し → auto_mount=falseのhostでもmount対象になる
9. 無引数はauto_mount=falseのhostを除外し、include_allで含める
10. 名指しが未知projectならServiceError
11. unmountはhost単位で一度だけ行い、workspace symlinkとmountpointを削除する
12. unmountはmountが作ったlink以外（実体・別を指すsymlink）に触れない
13. unmountは他のエントリを持つ親ディレクトリを残す
14. staleは--forceでunmountする
15. mount失敗時、作成したmountpointはrmdirされる（副作用境界）
16. mount失敗時、既存のmountpointは保持される（副作用境界）
17. post-mount probeがunreadableならcleanupして報告する
18. slow（健全だが高遅延）はprecheckでskipし再mountしない
19. post-mount probeがslowでもmount成功扱いとしcleanupしない
20. sshfs stderrはmount logへ永続化しない
21. host識別子はpath componentとして安全化される

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
from whub.services.remote.mount import (
    _mount_host,
    host_mount_id,
    host_mountpoint,
    host_volume_name,
    mount_targets,
    select_targets,
    unmount_targets,
)
from whub.models import Manifest
from whub.tests.helpers import manifest, manifest_data


def _manifest_without_auto_mount() -> Manifest:
    data = manifest_data()
    data["hosts"]["home"]["auto_mount"] = False
    return Manifest.model_validate(data)


@pytest.fixture(autouse=True)
def _disable_mount_log():
    with patch("whub.services.remote.mount.write_mount_log"):
        yield


@pytest.fixture
def _sshfs_installed():
    with patch("whub.services.remote.mount.shutil.which", return_value="/usr/bin/sshfs"):
        yield


def _statuses(results) -> list[str]:
    return [item.status for item in results]


def _relocate(m, name: str, root: Path) -> None:
    """Point one project's workspace path at an isolated temporary location."""
    m.resolve_project(name).resource._resolved_workspace_path = root / name


class TestHostIdentifiers:
    def test_host_mount_id_is_a_safe_path_component(self) -> None:
        # ケース21
        host_name = "../../outside"

        assert host_mount_id(host_name) == "host-..%2F..%2Foutside"
        assert host_volume_name(host_name) == "whub-host-..%2F..%2Foutside"

    def test_host_mountpoint_stays_under_runtime_mounts(self, tmp_path) -> None:
        context = WhubContext(tmp_path)
        with patch("whub.services.remote.mount.current_context", return_value=context):
            mountpoint = host_mountpoint("../../outside")

        assert mountpoint == (
            Path(tmp_path) / "runtime" / "mounts" / "host-..%2F..%2Foutside"
        )


class TestMountSpec:
    def test_mounts_host_once_and_links_workspace_path(
        self, tmp_path, _sshfs_installed
    ):
        # ケース1
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        resource = m.resolve_project("remote").resource
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                side_effect=[ResourceHealth("unmounted"), ResourceHealth("ok")],
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch(
                "whub.services.remote.mount.build_sshfs_command",
                return_value=["sshfs"],
            ) as build,
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
        ):
            results = mount_targets(m, "remote")

        assert _statuses(results) == ["mount"]
        assert resource._resolved_workspace_path.readlink() == mountpoint / "remote"
        assert build.call_args.args[1] == "/srv"

    def test_shares_one_sshfs_across_resources_of_a_host(
        self, tmp_path, _sshfs_installed
    ):
        # ケース2
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        _relocate(m, "nested", tmp_path / "workspace")
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                side_effect=[ResourceHealth("unmounted"), ResourceHealth("ok")],
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch(
                "whub.services.remote.mount.build_sshfs_command", return_value=["sshfs"]
            ) as build,
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ) as run,
        ):
            results = mount_targets(m, None, include_all=True)

        assert _statuses(results) == ["mount"]
        assert build.call_count == 1
        assert run.call_count == 1
        assert (tmp_path / "workspace" / "remote").readlink() == mountpoint / "remote"
        assert (tmp_path / "workspace" / "nested").readlink() == (
            mountpoint / "remote" / "nested"
        )

    def test_repairs_wrong_workspace_symlink_for_healthy_host(self, tmp_path):
        # ケース3
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_workspace_path.parent.mkdir(parents=True)
        resource._resolved_workspace_path.symlink_to(tmp_path / "wrong")
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("ok"),
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
        ):
            status = _mount_host("home", [(project, resource)])

        assert status == "skip"
        assert resource._resolved_workspace_path.readlink() == mountpoint / "remote"

    def test_refuses_to_replace_a_real_directory(self, tmp_path):
        # ケース4
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        project = m.resolve_project("remote")
        resource = project.resource
        resource._resolved_workspace_path.mkdir(parents=True)
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("ok"),
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
        ):
            status = _mount_host("home", [(project, resource)])

        assert status.startswith("FAIL: workspace path is not a symlink")
        assert resource._resolved_workspace_path.is_dir()
        assert not resource._resolved_workspace_path.is_symlink()

    def test_skips_when_already_mounted(self, tmp_path, _sshfs_installed):
        # ケース5
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("ok"),
            ),
            patch(
                "whub.services.remote.mount.host_mountpoint",
                return_value=tmp_path / "runtime" / "mounts" / "home",
            ),
        ):
            results = mount_targets(m, "remote")

        assert _statuses(results) == ["skip"]

    def test_stale_is_reported_without_mounting(self, _sshfs_installed):
        # ケース6
        m = manifest()
        mock_run = MagicMock()
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("stale"),
            ),
            patch("whub.services.remote.mount.subprocess.run", mock_run),
        ):
            results = mount_targets(m, "remote")

        assert results[0].status.startswith("STALE")
        assert not results[0].ok
        mock_run.assert_not_called()

    def test_sshfs_not_found_errors(self):
        # ケース7
        m = manifest()
        with patch("whub.services.remote.mount.shutil.which", return_value=None):
            with pytest.raises(ServiceError, match="sshfs not found"):
                mount_targets(m, None)

    def test_select_targets_by_name_ignores_auto_mount(self):
        # ケース8
        m = _manifest_without_auto_mount()
        targets = select_targets(m, "nested")

        assert len(targets) == 1
        assert targets[0][0].name == "nested"

    def test_select_targets_all_includes_hosts_without_auto_mount(self):
        # ケース9
        m = _manifest_without_auto_mount()
        targets_auto = select_targets(m, None, auto_only=True)
        targets_all = select_targets(m, None, auto_only=False)

        assert targets_auto == []
        assert {target[0].name for target in targets_all} == {"remote", "nested"}
        # auto_mountが既定(true)のhostは無引数でも対象になる
        assert len(select_targets(manifest(), None, auto_only=True)) == 2

    def test_select_targets_rejects_unknown_project(self):
        # ケース10
        m = manifest()
        with pytest.raises(ServiceError, match="unknown project"):
            select_targets(m, "no-such-project")

    def test_unmounts_host_once_and_removes_workspace_symlink(self, tmp_path):
        # ケース11
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        resource = m.resolve_project("remote").resource
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        mountpoint.mkdir(parents=True)
        resource._resolved_workspace_path.parent.mkdir(parents=True, exist_ok=True)
        resource._resolved_workspace_path.symlink_to(mountpoint / "remote")
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                side_effect=[ResourceHealth("ok"), ResourceHealth("unmounted")],
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch("whub.services.remote.mount.subprocess.run", mock_run),
        ):
            results = unmount_targets(m)

        assert _statuses(results) == ["unmount"]
        mock_run.assert_called_once_with(
            ["umount", str(mountpoint)],
            capture_output=True,
            text=True,
        )
        # dangling symlinkを残さない
        assert not resource._resolved_workspace_path.is_symlink()
        assert not resource._resolved_workspace_path.exists()
        assert not mountpoint.exists()

    def test_unmount_leaves_paths_it_does_not_own(self, tmp_path):
        # ケース12
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        _relocate(m, "nested", tmp_path / "workspace")
        remote = m.resolve_project("remote").resource
        nested = m.resolve_project("nested").resource
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        mountpoint.mkdir(parents=True)
        remote._resolved_workspace_path.parent.mkdir(parents=True, exist_ok=True)
        # 実ディレクトリと、別の場所を指すsymlinkはmountの所有物ではない
        remote._resolved_workspace_path.mkdir()
        nested._resolved_workspace_path.symlink_to(tmp_path / "elsewhere")
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                side_effect=[ResourceHealth("ok"), ResourceHealth("unmounted")],
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
        ):
            unmount_targets(m)

        assert remote._resolved_workspace_path.is_dir()
        assert nested._resolved_workspace_path.readlink() == tmp_path / "elsewhere"

    def test_unmount_keeps_parent_directory_holding_other_entries(self, tmp_path):
        # ケース13
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        resource = m.resolve_project("remote").resource
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        mountpoint.mkdir(parents=True)
        parent = resource._resolved_workspace_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        resource._resolved_workspace_path.symlink_to(mountpoint / "remote")
        (parent / "unrelated").write_text("keep me\n")
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                side_effect=[ResourceHealth("ok"), ResourceHealth("unmounted")],
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
        ):
            unmount_targets(m)

        assert not resource._resolved_workspace_path.is_symlink()
        assert (parent / "unrelated").read_text() == "keep me\n"

    def test_force_unmounts_stale_host(self, tmp_path):
        # ケース14
        m = manifest()
        mountpoint = tmp_path / "runtime" / "mounts" / "home"
        mountpoint.mkdir(parents=True)
        mock_run = MagicMock(return_value=CompletedProcess([], 0))
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                side_effect=[ResourceHealth("stale"), ResourceHealth("unmounted")],
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch("whub.services.remote.mount.subprocess.run", mock_run),
        ):
            results = unmount_targets(m, force=True)

        assert _statuses(results) == ["unmount"]
        mock_run.assert_called_once_with(
            ["umount", "-f", str(mountpoint)],
            capture_output=True,
            text=True,
        )

    def test_mount_failure_removes_created_mountpoint(self, tmp_path):
        # ケース15
        m = manifest()
        project = m.resolve_project("remote")
        mountpoint = tmp_path / "mnt"
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch("whub.services.remote.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", "failed"),
            ),
        ):
            status = _mount_host("home", [(project, project.resource)])

        assert status == "FAIL: failed"
        assert not mountpoint.exists()

    def test_mount_failure_keeps_existing_mountpoint(self, tmp_path):
        # ケース16
        m = manifest()
        project = m.resolve_project("remote")
        mountpoint = tmp_path / "mnt"
        mountpoint.mkdir()
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch("whub.services.remote.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", "failed"),
            ),
        ):
            status = _mount_host("home", [(project, project.resource)])

        assert status == "FAIL: failed"
        assert mountpoint.exists()

    def test_mount_readability_failure_unmounts_and_reports(self, tmp_path):
        # ケース17
        m = manifest()
        project = m.resolve_project("remote")
        mountpoint = tmp_path / "mnt"
        health_seq = [
            ResourceHealth("unmounted"),
            ResourceHealth(
                "unreadable",
                "Operation not permitted",
                "allow Network Volumes access, then remount",
            ),
        ]
        with (
            patch("whub.services.remote.mount.inspect_host_mount", side_effect=health_seq),
            patch("whub.services.remote.mount.host_mountpoint", return_value=mountpoint),
            patch("whub.services.remote.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
            patch(
                "whub.services.remote.mount._unmount_host", return_value="unmount"
            ) as cleanup,
        ):
            targets = [(project, project.resource)]
            status = _mount_host("home", targets)

        assert status == (
            "FAIL: mount unreadable: Operation not permitted; cleanup=unmount; "
            "recovery: allow Network Volumes access, then remount"
        )
        cleanup.assert_called_once_with("home", targets, force=True)

    def test_skips_when_mounted_but_slow(self, tmp_path, _sshfs_installed):
        # ケース18
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        mock_run = MagicMock()
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("slow", "directory listing exceeded 3s"),
            ),
            patch(
                "whub.services.remote.mount.host_mountpoint",
                return_value=tmp_path / "runtime" / "mounts" / "home",
            ),
            patch("whub.services.remote.mount.subprocess.run", mock_run),
        ):
            results = mount_targets(m, "remote")

        assert _statuses(results) == ["skip"]
        mock_run.assert_not_called()

    def test_slow_post_mount_probe_succeeds_without_cleanup(self, tmp_path):
        # ケース19
        m = manifest()
        _relocate(m, "remote", tmp_path / "workspace")
        project = m.resolve_project("remote")
        health_seq = [
            ResourceHealth("unmounted"),
            ResourceHealth("slow", "directory listing exceeded 3s"),
        ]
        with (
            patch("whub.services.remote.mount.inspect_host_mount", side_effect=health_seq),
            patch(
                "whub.services.remote.mount.host_mountpoint",
                return_value=tmp_path / "runtime" / "mounts" / "home",
            ),
            patch("whub.services.remote.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 0),
            ),
            patch("whub.services.remote.mount._unmount_host") as cleanup,
        ):
            status = _mount_host("home", [(project, project.resource)])

        assert status == "mount"
        cleanup.assert_not_called()

    def test_sshfs_stderr_is_not_persisted(self, tmp_path):
        # ケース20
        m = manifest()
        project = m.resolve_project("remote")
        secret = "user@host:/private/path IdentityFile=/Users/private/key"
        with (
            patch(
                "whub.services.remote.mount.inspect_host_mount",
                return_value=ResourceHealth("unmounted"),
            ),
            patch("whub.services.remote.mount.host_mountpoint", return_value=tmp_path / "mnt"),
            patch("whub.services.remote.mount.build_sshfs_command", return_value=["sshfs"]),
            patch(
                "whub.services.remote.mount.subprocess.run",
                return_value=CompletedProcess([], 1, "", secret),
            ),
            patch("whub.services.remote.mount.write_mount_log") as write_log,
        ):
            _mount_host("home", [(project, project.resource)])

        sshfs_record = next(
            call.kwargs
            for call in write_log.call_args_list
            if call.kwargs["stage"] == "sshfs"
        )
        assert sshfs_record["detail"] == "sshfs command failed"
        assert secret not in repr(sshfs_record)
