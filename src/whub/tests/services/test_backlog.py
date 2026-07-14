"""Backlog service behavior tests.

検証するケース:
1. local backlogの追記とマーカー不正エラー
2. remote backlogのSSH経由書込内容
3. local/remote backlogの読取とmount未済エラー
"""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from whub.services.backlog import MARKERS, append_backlog, read_backlog
from whub.services.errors import ServiceError
from whub.tests.helpers import manifest
from whub.utils.managed_block import format_block


def test_local_backlog_appends_and_validates_markers(tmp_path: Path) -> None:
    # ケース1
    loaded_manifest = manifest()
    project = loaded_manifest.resolve_project("local")
    assert project is not None
    assert project.resource is not None
    project.resource.source = str(tmp_path)
    backlog = tmp_path / "docs" / "backlog.md"
    backlog.parent.mkdir()
    backlog.write_text(format_block(MARKERS, "existing"))

    append_backlog(loaded_manifest, "local", "new memo")

    assert backlog.read_text() == format_block(MARKERS, "existing\n- new memo")

    backlog.write_text("no markers\n")
    with pytest.raises(ServiceError, match="markers are missing or duplicated"):
        append_backlog(loaded_manifest, "local", "another memo")


def test_remote_backlog_writes_marker_content() -> None:
    # ケース2
    content = format_block(MARKERS, "existing")

    def run_ssh(host, command: str, **kwargs) -> CompletedProcess[str]:
        del host, kwargs
        if "test -d" in command:
            return CompletedProcess([], 0)
        if "if test -f" in command:
            return CompletedProcess([], 0, stdout="file\n")
        if command.startswith("cat "):
            return CompletedProcess([], 0, stdout=content)
        if "cat >" in command:
            return CompletedProcess([], 0)
        raise AssertionError(f"unexpected SSH command: {command}")

    with patch("whub.services.backlog.run_ssh_command", side_effect=run_ssh) as mock_ssh:
        append_backlog(manifest(), "remote", "new memo")

    write = mock_ssh.call_args_list[-1]
    assert write.kwargs["input"] == format_block(MARKERS, "existing\n- new memo")


def test_read_local_backlog_returns_content_or_empty(tmp_path: Path) -> None:
    # ケース3
    loaded_manifest = manifest()
    project = loaded_manifest.resolve_project("local")
    assert project is not None
    assert project.resource is not None
    project.resource.source = str(tmp_path)

    assert read_backlog(loaded_manifest, "local") == ""

    backlog = tmp_path / "docs" / "backlog.md"
    backlog.parent.mkdir()
    backlog.write_text("local memo\n")

    assert read_backlog(loaded_manifest, "local") == "local memo\n"


def test_read_remote_backlog_uses_mounted_workspace(tmp_path: Path) -> None:
    # ケース3
    loaded_manifest = manifest()
    project = loaded_manifest.resolve_project("remote")
    assert project is not None
    assert project.resource is not None
    resource = project.resource
    resource._resolved_workspace_path = tmp_path / "remote-mount"

    with pytest.raises(ServiceError, match="remote workspace path is not available"):
        read_backlog(loaded_manifest, "remote")

    resource._resolved_workspace_path.mkdir()
    backlog = resource._resolved_workspace_path / "docs" / "backlog.md"
    backlog.parent.mkdir()
    backlog.write_text("remote memo\n")

    assert read_backlog(loaded_manifest, "remote") == "remote memo\n"
