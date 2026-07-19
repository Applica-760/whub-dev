"""Project content resource resolution tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from whub.models import Project, RemoteResource, SymlinkResource
from whub.services.errors import ServiceError
from whub.services.project_content import resolve_project_content_resource
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
