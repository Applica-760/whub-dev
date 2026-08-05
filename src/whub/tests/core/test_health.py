"""`whub.core.health`の仕様テスト。

検証するケース:
1. `inspect_symlink()`はsourceが存在しない場合、`source-missing`を返す。
2. `inspect_symlink()`はtargetが正しいsymlinkなら`ok`を返す。
3. `inspect_symlink()`はtarget symlinkが壊れていれば`broken`を返す。
4. `inspect_symlink()`はtarget symlinkが別sourceを指していれば`wrong-target`を返す。
5. `inspect_symlink()`はtargetに通常ファイル/ディレクトリがあれば`unexpected`を返す。
6. `inspect_symlink()`はtargetが存在しなければ`missing`を返す。
7. `_read_mount_table()`は`mount`成功時にstdoutを返す。
8. `_read_mount_table()`は`mount`失敗・timeout・OSError時に`None`を返す。
9. `inspect_mountpoint()`はmount tableが読めなければfail-safeで`stale`を返す。
10. `inspect_mountpoint()`はmount tableにmountpointがなければ`unmounted`を返す。
11. `inspect_mountpoint()`はmount tableにmountpointがあり、sshfsプロセスと`stat`が成功なら`ok`を返す。
12. `inspect_mountpoint()`はsshfsプロセス不在・検査失敗なら`stale`を返す。
13. `inspect_mountpoint()`は`stat` timeout/OSError/CalledProcessErrorなら`stale`を返す。
14. `inspect_mountpoint()`は指定volnameで既存の遅延非障害契約を適用する。

検証しないケース:
1. 実mount tableのOSごとの差異。
2. 実stale mountによるハング再現。
3. mountpoint文字列に改行などが含まれる異常系。
4. `Path.resolve()`自体の挙動。
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import whub.core.health as health_module
from whub.core.health import (
    _read_mount_table,
    inspect_aggregated_mount,
    inspect_mountpoint,
    inspect_symlink,
)
from whub.models import Host, RemoteResource, SymlinkResource


def _symlink_resource(source: Path, target: Path) -> SymlinkResource:
    resource = SymlinkResource(
        type="symlink",
        workspace_path="projects/local",
        source=str(source),
    )
    resource._resolved_workspace_path = target
    return resource


def _remote_resource(mountpoint: Path) -> RemoteResource:
    resource = RemoteResource(
        type="remote",
        host="home",
        path="remote",
        workspace_path="projects/remote",
    )
    resource._resolved_workspace_path = mountpoint
    return resource


def _aggregated_resource(workspace_path: Path) -> RemoteResource:
    resource = _remote_resource(workspace_path)
    resource._resolved_host = Host(
        hostname="ssh.test.invalid",
        user="test-user",
        identity_file="/test/identity",
        mount_root="/srv",
        worktree_root="worktrees",
        )
    return resource


class TestSymlinkHealthSpec:
    def test_source_missing_reports_source_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース1
            root = Path(tmp)
            health = inspect_symlink(
                _symlink_resource(root / "missing-source", root / "target")
            )

        assert health.state == "source-missing"

    def test_correct_symlink_reports_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース2
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.symlink_to(source)
            health = inspect_symlink(_symlink_resource(source, target))

        assert health.state == "ok"

    def test_broken_symlink_reports_broken(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース3
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.symlink_to(root / "missing-target")
            health = inspect_symlink(_symlink_resource(source, target))

        assert health.state == "broken"

    def test_wrong_symlink_target_reports_wrong_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース4
            root = Path(tmp)
            source = root / "source"
            other = root / "other"
            target = root / "target"
            source.mkdir()
            other.mkdir()
            target.symlink_to(other)
            health = inspect_symlink(_symlink_resource(source, target))

        assert health.state == "wrong-target"

    def test_existing_non_symlink_target_reports_unexpected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース5
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.write_text("file")
            health = inspect_symlink(_symlink_resource(source, target))

        assert health.state == "unexpected"

    def test_missing_target_reports_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース6
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            health = inspect_symlink(_symlink_resource(source, target))

        assert health.state == "missing"


class TestMountHealthSpec:
    def test_read_mount_table_returns_stdout_when_mount_succeeds(self) -> None:
        # ケース7
        completed = subprocess.CompletedProcess(["mount"], 0, "mount output", "")
        with patch.object(health_module.subprocess, "run", return_value=completed):
            assert _read_mount_table() == "mount output"

    def test_read_mount_table_returns_none_when_mount_cannot_be_read(self) -> None:
        # ケース8
        cases = (
            subprocess.CompletedProcess(["mount"], 1, "", "failed"),
            subprocess.TimeoutExpired(["mount"], 5),
            OSError("missing mount"),
        )
        for case in cases:
            if isinstance(case, subprocess.CompletedProcess):
                patcher = patch.object(
                    health_module.subprocess, "run", return_value=case
                )
            else:
                patcher = patch.object(
                    health_module.subprocess, "run", side_effect=case
                )
            with patcher:
                assert _read_mount_table() is None

    def test_mount_table_unreadable_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース9
            mountpoint = Path(tmp) / "remote"
            with patch.object(health_module, "_read_mount_table", return_value=None):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "stale"

    def test_mountpoint_absent_from_table_reports_unmounted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース10
            mountpoint = Path(tmp) / "remote"
            table = "/dev/disk1 on /other/path (apfs, local)\n"
            with patch.object(health_module, "_read_mount_table", return_value=table):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "unmounted"

    def test_mountpoint_in_table_and_stat_success_reports_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース11
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            process = subprocess.CompletedProcess(["pgrep"], 0, "", "")
            stat = subprocess.CompletedProcess(["stat"], 0, "", "")
            listing = subprocess.CompletedProcess(["ls"], 0, "", "")
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess,
                    "run",
                    side_effect=[process, stat, listing],
                ),
            ):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "ok"

    def test_mountpoint_in_table_and_missing_sshfs_process_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース12
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            missing = subprocess.CompletedProcess(["pgrep"], 1, "", "")
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess, "run", return_value=missing
                ) as run,
            ):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "stale"
        run.assert_called_once_with(
            ["pgrep", "-f", "volname=whub-remote"],
            capture_output=True,
            timeout=3,
        )

    def test_mountpoint_in_table_and_sshfs_process_check_failure_reports_stale(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース12
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            cases = (OSError("pgrep failed"), subprocess.TimeoutExpired(["pgrep"], 3))
            for case in cases:
                with (
                    patch.object(
                        health_module, "_read_mount_table", return_value=table
                    ),
                    patch.object(health_module.subprocess, "run", side_effect=case),
                ):
                    health = inspect_mountpoint(mountpoint, "whub-remote")
                assert health.state == "stale"

    def test_child_listing_failure_reports_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess(["pgrep"], 0, "", ""),
                        subprocess.CompletedProcess(["stat"], 0, "", ""),
                        subprocess.CompletedProcess(
                            ["ls"], 1, "", "Operation not permitted"
                        ),
                    ],
                ),
            ):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "unreadable"
        assert health.detail == "Operation not permitted"
        assert "Network Volumes" in health.recovery

    def test_mountpoint_in_table_and_stat_failure_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース13
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            cases = (
                OSError("stat failed"),
                subprocess.CalledProcessError(1, ["stat"], stderr="failed"),
            )
            for case in cases:
                with (
                    patch.object(
                        health_module, "_read_mount_table", return_value=table
                    ),
                    patch.object(
                        health_module.subprocess,
                        "run",
                        side_effect=[
                            subprocess.CompletedProcess(["pgrep"], 0, "", ""),
                            case,
                        ],
                    ),
                ):
                    health = inspect_mountpoint(mountpoint, "whub-remote")
                assert health.state == "stale"

    def test_stat_timeout_with_live_process_reports_slow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース14: レイテンシ非依存契約 — timeoutは障害根拠にしない
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess(["pgrep"], 0, "", ""),
                        subprocess.TimeoutExpired(["stat"], 3),
                    ],
                ),
            ):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "slow"
        assert health.recovery is None

    def test_child_listing_timeout_reports_slow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース14: レイテンシ非依存契約 — timeoutは障害根拠にしない
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess(["pgrep"], 0, "", ""),
                        subprocess.CompletedProcess(["stat"], 0, "", ""),
                        subprocess.TimeoutExpired(["ls"], 3),
                    ],
                ),
            ):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "slow"
        assert "exceeded 3s" in health.detail
        assert health.recovery is None

    def test_child_listing_generic_error_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # denied以外の即時エラーはstale（自動cleanup対象にしない）
            mountpoint = Path(tmp) / "remote"
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess(["pgrep"], 0, "", ""),
                        subprocess.CompletedProcess(["stat"], 0, "", ""),
                        subprocess.CompletedProcess(
                            ["ls"], 1, "", "Input/output error"
                        ),
                    ],
                ),
            ):
                health = inspect_mountpoint(mountpoint, "whub-remote")

        assert health.state == "stale"
        assert health.detail == "Input/output error"
        assert "unmount --force" in health.recovery


class TestHostMountHealthSpec:
    def test_host_mount_uses_host_volume_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp) / "home"
            table = f"server:/srv on {mountpoint} (macfuse)\n"
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess(["pgrep"], 0, "", ""),
                        subprocess.CompletedProcess(["stat"], 0, "", ""),
                        subprocess.CompletedProcess(["ls"], 0, "", ""),
                    ],
                ) as run,
            ):
                health = inspect_mountpoint(mountpoint, "whub-host-home")

        assert health.state == "ok"
        assert run.call_args_list[0].args[0] == [
            "pgrep",
            "-f",
            "volname=whub-host-home",
        ]

    def test_host_mount_absent_from_table_reports_unmounted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp) / "home"
            with patch.object(
                health_module,
                "_read_mount_table",
                return_value="/dev/disk1 on /other/path (apfs, local)\n",
            ):
                health = inspect_mountpoint(mountpoint, "whub-host-home")

        assert health.state == "unmounted"

    def test_host_mount_stat_timeout_reports_slow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mountpoint = Path(tmp) / "home"
            table = f"server:/srv on {mountpoint} (macfuse)\n"
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(
                    health_module.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess(["pgrep"], 0, "", ""),
                        subprocess.TimeoutExpired(["stat"], 3),
                    ],
                ),
            ):
                health = inspect_mountpoint(mountpoint, "whub-host-home")

        assert health.state == "slow"


class TestAggregatedMountHealthSpec:
    def test_correct_symlink_and_healthy_host_reports_ok(self, tmp_path) -> None:
        host_mountpoint = tmp_path / "runtime" / "home"
        source = host_mountpoint / "remote"
        target = tmp_path / "workspace" / "remote"
        target.parent.mkdir(parents=True)
        target.symlink_to(source)
        with (
            patch.object(
                health_module,
                "inspect_mountpoint",
                return_value=health_module.ResourceHealth("ok"),
            ),
            patch.object(
                health_module.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(["stat"], 0, "", ""),
            ),
        ):
            health = inspect_aggregated_mount(
                _aggregated_resource(target),
                host_mountpoint,
                "whub-host-home",
            )

        assert health.state == "ok"

    def test_wrong_workspace_symlink_reports_wrong_target(self, tmp_path) -> None:
        host_mountpoint = tmp_path / "runtime" / "home"
        target = tmp_path / "workspace" / "remote"
        target.parent.mkdir(parents=True)
        target.symlink_to(tmp_path / "wrong")
        with patch.object(health_module, "inspect_mountpoint") as host_health:
            health = inspect_aggregated_mount(
                _aggregated_resource(target),
                host_mountpoint,
                "whub-host-home",
            )

        assert health.state == "wrong-target"
        host_health.assert_not_called()

    def test_unmounted_host_overrides_correct_broken_symlink(self, tmp_path) -> None:
        host_mountpoint = tmp_path / "runtime" / "home"
        target = tmp_path / "workspace" / "remote"
        target.parent.mkdir(parents=True)
        target.symlink_to(host_mountpoint / "remote")
        with patch.object(
            health_module,
            "inspect_mountpoint",
            return_value=health_module.ResourceHealth("unmounted"),
        ):
            health = inspect_aggregated_mount(
                _aggregated_resource(target),
                host_mountpoint,
                "whub-host-home",
            )

        assert health.state == "unmounted"

    def test_missing_shared_target_reports_broken(self, tmp_path) -> None:
        host_mountpoint = tmp_path / "runtime" / "home"
        target = tmp_path / "workspace" / "remote"
        target.parent.mkdir(parents=True)
        target.symlink_to(host_mountpoint / "remote")
        with (
            patch.object(
                health_module,
                "inspect_mountpoint",
                return_value=health_module.ResourceHealth("ok"),
            ),
            patch.object(
                health_module.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    ["stat"], 1, "", "No such file or directory"
                ),
            ),
        ):
            health = inspect_aggregated_mount(
                _aggregated_resource(target),
                host_mountpoint,
                "whub-host-home",
            )

        assert health.state == "broken"
