"""Resource status collection tests."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from whub.core.health import ResourceHealth
from whub.models import GitInfo, Manifest, ResourceStatus, WorktreeStatus
from whub.services.status import _parse_probe, collect_resource_status, collect_status
from whub.tests.helpers import manifest


def _symlink_ok(_resource) -> ResourceHealth:
    return ResourceHealth("ok")


def _mount_ok(_resource, _mountpoint, _volname) -> ResourceHealth:
    return ResourceHealth("ok")


def test_collects_local_and_remote_statuses() -> None:
    m = manifest()
    project = m.resolve_project("remote")
    assert project is not None
    assert project.resource is not None
    project.resource.git = GitInfo(url="git@example.com:remote.git")
    probe_data = {0: ("ok", "3", "on"), 1: ("ok", "0", "-")}
    with (
        patch("whub.services.status.inspect_symlink", _symlink_ok),
        patch("whub.services.status.inspect_aggregated_mount", _mount_ok),
        patch("whub.services.status._probe_host", return_value=probe_data),
        patch(
            "whub.services.status.subprocess.run",
            return_value=CompletedProcess([], 0, stdout=""),
        ),
    ):
        statuses = collect_resource_status(m)

    assert [(item.project, item.state, item.type) for item in statuses] == [
        ("local", "ok", "symlink"),
        ("remote", "ok", "remote"),
        ("nested", "ok", "remote"),
    ]
    assert statuses[1].tmux == "on"
    assert statuses[1].git == "3 files"


def test_returns_empty_list_without_resources() -> None:
    assert collect_resource_status(Manifest(projects=[])) == []


def test_collect_status_attaches_worktrees_to_their_parent_resource(tmp_path) -> None:
    resources = [ResourceStatus("local", "ok", "symlink")]
    attached = WorktreeStatus(
        "local", "TASK-075", "tasks/075", "projects/worktrees/local-075"
    )
    invalid = WorktreeStatus(
        None, None, None, None, ("invalid worktree definition YAML: invalid.yaml",)
    )
    with (
        patch("whub.services.status.collect_resource_status", return_value=resources),
        patch(
            "whub.services.status.collect_worktree_status",
            return_value=[attached, invalid],
        ),
    ):
        report = collect_status(manifest(), tmp_path)

    assert report.resources[0].worktrees == (attached,)
    assert report.invalid_worktrees == (invalid,)
    assert report.unhealthy


def test_marks_unreachable_remote_and_preserves_mount_state() -> None:
    with (
        patch("whub.services.status.inspect_symlink", _symlink_ok),
        patch(
            "whub.services.status.inspect_aggregated_mount",
            return_value=ResourceHealth("stale"),
        ),
        patch("whub.services.status._probe_host", return_value=None),
    ):
        statuses = collect_resource_status(manifest())

    remote = next(item for item in statuses if item.project == "remote")
    assert remote.state == "unreachable"
    assert remote.mount == "stale"


def test_uses_aggregated_health_for_every_remote_resource() -> None:
    m = manifest()
    with (
        patch("whub.services.status.inspect_symlink", _symlink_ok),
        patch(
            "whub.services.status.inspect_aggregated_mount",
            return_value=ResourceHealth("slow"),
        ) as aggregated,
        patch(
            "whub.services.status._probe_host",
            return_value={0: ("ok", "0", "-"), 1: ("ok", "0", "-")},
        ),
    ):
        statuses = collect_resource_status(m)

    remote = next(item for item in statuses if item.project == "remote")
    nested = next(item for item in statuses if item.project == "nested")
    # nestedも共有host mount越しに解決するため合成healthで判定する
    assert remote.mount == "slow"
    assert nested.mount == "slow"
    assert aggregated.call_count == 2


def test_parse_probe_accepts_valid_lines_and_ignores_invalid_lines() -> None:
    parsed = _parse_probe("R0 ok 3 on\nbogus line\n\nR1 missing ?\n")

    assert parsed == {0: ("ok", "3", "on")}


def test_marks_local_git_failure() -> None:
    m = manifest()
    project = m.resolve_project("local")
    assert project is not None
    assert project.resource is not None
    project.resource.git = GitInfo(url="git@example.com:local.git")
    with (
        patch("whub.services.status.inspect_symlink", _symlink_ok),
        patch("whub.services.status.inspect_aggregated_mount", _mount_ok),
        patch("whub.services.status._probe_host", return_value={0: ("ok", "0", "-")}),
        patch(
            "whub.services.status.subprocess.run",
            return_value=CompletedProcess([], 1, stdout=""),
        ),
    ):
        statuses = collect_resource_status(m)

    local = next(item for item in statuses if item.project == "local")
    assert local.git == "failed"


def test_marks_remote_git_failure() -> None:
    m = manifest()
    project = m.resolve_project("remote")
    assert project is not None
    assert project.resource is not None
    project.resource.git = GitInfo(url="git@example.com:remote.git")
    with (
        patch("whub.services.status.inspect_symlink", _symlink_ok),
        patch("whub.services.status.inspect_aggregated_mount", _mount_ok),
        patch("whub.services.status._probe_host", return_value={0: ("ok", "?", "-")}),
        patch(
            "whub.services.status.subprocess.run",
            return_value=CompletedProcess([], 0, stdout=""),
        ),
    ):
        statuses = collect_resource_status(m)

    remote = next(item for item in statuses if item.project == "remote")
    assert remote.git == "failed"
