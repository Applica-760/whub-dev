"""`whub mount`/`whub unmount`のCLI境界テスト。

検証するケース:
1. mountはCLI引数をserviceへ渡し、結果を表に描画する
2. unmountは--forceをserviceへ渡し、結果を表に描画する
3. 失敗結果があるとexit code 1になる
4. remote resourceが無いときの案内表示
5. ServiceErrorはClickExceptionとして表示される

検証しないケース:
- mount/unmountのオーケストレーション（services/test_mount.pyが担当）
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.remote.mount import mount, unmount
from whub.services.errors import ServiceError
from whub.services.remote.mount import MountResult
from whub.tests.helpers import manifest


class TestMountCommandSpec:
    def test_passes_arguments_to_service_and_renders(self):
        # ケース1
        m = manifest()
        with (
            patch("whub.commands.remote.mount.get_manifest", return_value=m),
            patch(
                "whub.commands.remote.mount.mount_targets",
                return_value=[MountResult("remote", "mount")],
            ) as service,
        ):
            result = CliRunner().invoke(mount, ["remote", "-a"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "mount" in result.output
        assert "remote" in result.output
        service.assert_called_once_with(m, "remote", include_all=True)

    def test_unmount_passes_force_to_service(self):
        # ケース2
        m = manifest()
        with (
            patch("whub.commands.remote.mount.get_manifest", return_value=m),
            patch(
                "whub.commands.remote.mount.unmount_targets",
                return_value=[MountResult("remote", "unmount")],
            ) as service,
        ):
            result = CliRunner().invoke(unmount, ["--force"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "unmount" in result.output
        service.assert_called_once_with(m, force=True)

    def test_failure_result_exits_non_zero(self):
        # ケース3
        m = manifest()
        with (
            patch("whub.commands.remote.mount.get_manifest", return_value=m),
            patch(
                "whub.commands.remote.mount.mount_targets",
                return_value=[MountResult("remote", "FAIL: broken")],
            ),
        ):
            result = CliRunner().invoke(mount, [])

        assert result.exit_code == 1
        assert "FAIL: broken" in result.output

    def test_reports_when_no_remote_resources(self):
        # ケース4
        m = manifest()
        with (
            patch("whub.commands.remote.mount.get_manifest", return_value=m),
            patch("whub.commands.remote.mount.mount_targets", return_value=[]),
        ):
            result = CliRunner().invoke(mount, [], catch_exceptions=False)

        assert result.exit_code == 0
        assert "(no remote resources)" in result.output

    def test_service_error_is_reported_as_click_error(self):
        # ケース5
        m = manifest()
        with (
            patch("whub.commands.remote.mount.get_manifest", return_value=m),
            patch(
                "whub.commands.remote.mount.mount_targets",
                side_effect=ServiceError("sshfs not found"),
            ),
        ):
            result = CliRunner().invoke(mount, [])

        assert result.exit_code != 0
        assert "sshfs not found" in result.output
