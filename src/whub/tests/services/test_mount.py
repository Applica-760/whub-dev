"""Shared host mount identifier tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from whub.core.context import WhubContext
from whub.services.mount import host_mount_id, host_mountpoint, host_volume_name


def test_host_mount_id_is_a_safe_path_component() -> None:
    host_name = "../../outside"

    assert host_mount_id(host_name) == "host-..%2F..%2Foutside"
    assert host_volume_name(host_name) == "whub-host-..%2F..%2Foutside"


def test_host_mountpoint_stays_under_runtime_mounts(tmp_path) -> None:
    context = WhubContext(tmp_path)
    with patch("whub.services.mount.current_context", return_value=context):
        mountpoint = host_mountpoint("../../outside")

    assert mountpoint == (
        Path(tmp_path) / "runtime" / "mounts" / "host-..%2F..%2Foutside"
    )
