"""Project content resource resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.models import Project, RemoteResource, SymlinkResource
from whub.services.errors import ServiceError
from whub.services.project_content import (
    resolve_project_content_resource,
    resolve_project_content_root,
)
from whub.tests.helpers import manifest


def test_resolves_declared_local_and_remote_resources() -> None:
    loaded_manifest = manifest()

    assert isinstance(
        resolve_project_content_resource(loaded_manifest, "local"),
        SymlinkResource,
    )
    assert isinstance(
        resolve_project_content_resource(loaded_manifest, "remote"),
        RemoteResource,
    )


def test_rejects_unknown_and_resourceless_projects() -> None:
    loaded_manifest = manifest()
    loaded_manifest.projects.append(Project(name="workspace-hub"))

    with pytest.raises(ServiceError, match="unknown project: missing"):
        resolve_project_content_resource(loaded_manifest, "missing")
    with pytest.raises(ServiceError, match="project has no resource: no-resource"):
        resolve_project_content_resource(loaded_manifest, "no-resource")
    with pytest.raises(ServiceError, match="project has no resource: workspace-hub"):
        resolve_project_content_resource(loaded_manifest, "workspace-hub")


def test_resolves_available_project_content_roots(
    tmp_path: Path,
) -> None:
    loaded_manifest = manifest()
    local = loaded_manifest.resolve_project("local")
    remote = loaded_manifest.resolve_project("remote")
    local.resource.source = str(tmp_path / "local-source")
    remote.resource._resolved_workspace_path = tmp_path / "remote-mount"
    Path(local.resource.source).mkdir()
    remote.resource._resolved_workspace_path.mkdir()

    assert resolve_project_content_root(loaded_manifest, "local") == Path(
        local.resource.source
    )
    assert (
        resolve_project_content_root(loaded_manifest, "remote")
        == remote.resource._resolved_workspace_path
    )


def test_rejects_unavailable_project_content_root() -> None:
    with pytest.raises(
        ServiceError,
        match="project resource is not available: remote",
    ):
        resolve_project_content_root(manifest(), "remote")


def test_rejects_unreadable_project_content_root(tmp_path: Path) -> None:
    loaded_manifest = manifest()
    remote = loaded_manifest.resolve_project("remote")
    remote.resource._resolved_workspace_path = tmp_path

    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        pytest.raises(
            ServiceError, match="project resource is unreadable.*Network Volumes"
        ),
    ):
        monkeypatch.setattr(
            "whub.services.project_content.probe_directory_readable",
            lambda path: "Operation not permitted",
        )
        resolve_project_content_root(loaded_manifest, "remote")


def test_local_unreadable_recovery_uses_filesystem_permissions(tmp_path: Path) -> None:
    loaded_manifest = manifest()
    local = loaded_manifest.resolve_project("local")
    local.resource.source = str(tmp_path)

    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        pytest.raises(ServiceError, match="check local filesystem permissions"),
    ):
        monkeypatch.setattr(
            "whub.services.project_content.probe_directory_readable",
            lambda path: "Permission denied",
        )
        resolve_project_content_root(loaded_manifest, "local")
