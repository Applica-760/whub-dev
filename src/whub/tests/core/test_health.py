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
9. `inspect_mount()`はmount tableが読めなければfail-safeで`stale`を返す。
10. `inspect_mount()`はmount tableにmountpointがなければ`unmounted`を返す。
11. `inspect_mount()`はmount tableにmountpointがあり、sshfsプロセスと`stat`が成功なら`ok`を返す。
12. `inspect_mount()`はsshfsプロセス不在・検査失敗なら`stale`を返す。
13. `inspect_mount()`は`stat` timeout/OSError/CalledProcessErrorなら`stale`を返す。

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
from whub.core.health import _read_mount_table, inspect_mount, inspect_symlink
from whub.models import RemoteResource, SymlinkResource


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
        path="/srv/remote",
        workspace_path="projects/remote",
    )
    resource._resolved_workspace_path = mountpoint
    return resource


class TestSymlinkHealthSpec:
    def test_source_missing_reports_source_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース1
            root = Path(tmp)
            health = inspect_symlink(_symlink_resource(root / "missing-source", root / "target"))

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
                patcher = patch.object(health_module.subprocess, "run", return_value=case)
            else:
                patcher = patch.object(health_module.subprocess, "run", side_effect=case)
            with patcher:
                assert _read_mount_table() is None

    def test_mount_table_unreadable_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース9
            resource = _remote_resource(Path(tmp) / "remote")
            with patch.object(health_module, "_read_mount_table", return_value=None):
                health = inspect_mount(resource, "remote")

        assert health.state == "stale"

    def test_mountpoint_absent_from_table_reports_unmounted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース10
            resource = _remote_resource(Path(tmp) / "remote")
            table = "/dev/disk1 on /other/path (apfs, local)\n"
            with patch.object(health_module, "_read_mount_table", return_value=table):
                health = inspect_mount(resource, "remote")

        assert health.state == "unmounted"

    def test_mountpoint_in_table_and_stat_success_reports_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース11
            mountpoint = Path(tmp) / "remote"
            resource = _remote_resource(mountpoint)
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            process = subprocess.CompletedProcess(["pgrep"], 0, "", "")
            stat = subprocess.CompletedProcess(["stat"], 0, "", "")
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(health_module.subprocess, "run", side_effect=[process, stat]),
            ):
                health = inspect_mount(resource, "remote")

        assert health.state == "ok"

    def test_mountpoint_in_table_and_missing_sshfs_process_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース12
            mountpoint = Path(tmp) / "remote"
            resource = _remote_resource(mountpoint)
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            missing = subprocess.CompletedProcess(["pgrep"], 1, "", "")
            with (
                patch.object(health_module, "_read_mount_table", return_value=table),
                patch.object(health_module.subprocess, "run", return_value=missing) as run,
            ):
                health = inspect_mount(resource, "remote")

        assert health.state == "stale"
        run.assert_called_once_with(
            ["pgrep", "-f", "volname=whub-remote"],
            capture_output=True,
            timeout=3,
        )

    def test_mountpoint_in_table_and_sshfs_process_check_failure_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース12
            mountpoint = Path(tmp) / "remote"
            resource = _remote_resource(mountpoint)
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            cases = (OSError("pgrep failed"), subprocess.TimeoutExpired(["pgrep"], 3))
            for case in cases:
                with (
                    patch.object(health_module, "_read_mount_table", return_value=table),
                    patch.object(health_module.subprocess, "run", side_effect=case),
                ):
                    health = inspect_mount(resource, "remote")
                assert health.state == "stale"

    def test_mountpoint_in_table_and_stat_failure_reports_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # ケース13
            mountpoint = Path(tmp) / "remote"
            resource = _remote_resource(mountpoint)
            table = f"server:/srv/remote on {mountpoint} (macfuse)\n"
            cases = (
                subprocess.TimeoutExpired(["stat"], 3),
                OSError("stat failed"),
                subprocess.CalledProcessError(1, ["stat"], stderr="failed"),
            )
            for case in cases:
                with (
                    patch.object(health_module, "_read_mount_table", return_value=table),
                    patch.object(
                        health_module.subprocess,
                        "run",
                        side_effect=[subprocess.CompletedProcess(["pgrep"], 0, "", ""), case],
                    ),
                ):
                    health = inspect_mount(resource, "remote")
                assert health.state == "stale"
