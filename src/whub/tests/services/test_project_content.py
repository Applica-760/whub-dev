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


def test_resolves_local_remote_and_workspace_hub_resources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path))
    loaded_manifest = manifest()
    loaded_manifest.projects.append(Project(name="workspace-hub"))

    assert isinstance(
        resolve_project_content_resource(loaded_manifest, "local"),
        SymlinkResource,
    )
    assert isinstance(
        resolve_project_content_resource(loaded_manifest, "remote"),
        RemoteResource,
    )

    workspace_hub = resolve_project_content_resource(
        loaded_manifest,
        "workspace-hub",
    )
    assert isinstance(workspace_hub, SymlinkResource)
    assert workspace_hub.source == str(tmp_path)


def test_rejects_unknown_and_resourceless_projects() -> None:
    loaded_manifest = manifest()

    with pytest.raises(ServiceError, match="unknown project: missing"):
        resolve_project_content_resource(loaded_manifest, "missing")
    with pytest.raises(ServiceError, match="project has no resource: no-resource"):
        resolve_project_content_resource(loaded_manifest, "no-resource")


def test_resolves_available_project_content_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHUB_ROOT", str(tmp_path))
    loaded_manifest = manifest()
    local = loaded_manifest.resolve_project("local")
    remote = loaded_manifest.resolve_project("remote")
    local.resource.source = str(tmp_path / "local-source")
    remote.resource._resolved_workspace_path = tmp_path / "remote-mount"
    loaded_manifest.projects.append(Project(name="workspace-hub"))
    Path(local.resource.source).mkdir()
    remote.resource._resolved_workspace_path.mkdir()

    assert resolve_project_content_root(loaded_manifest, "local") == Path(
        local.resource.source
    )
    assert (
        resolve_project_content_root(loaded_manifest, "remote")
        == remote.resource._resolved_workspace_path
    )
    assert resolve_project_content_root(loaded_manifest, "workspace-hub") == tmp_path


def test_rejects_unavailable_project_content_root() -> None:
    with pytest.raises(
        ServiceError,
        match="project resource is not available: remote",
    ):
        resolve_project_content_root(manifest(), "remote")
