import pytest

from whub.models import Manifest, SymlinkResource
from whub.services.errors import ServiceError
from whub.services.worktree import require_worktree_parent
from whub.tests.helpers import manifest_data


def local_git_manifest() -> Manifest:
    data = manifest_data()
    data["projects"][0]["resource"]["git"] = {"url": "git@example.com:local.git"}
    return Manifest.model_validate(data)


def test_require_worktree_parent_accepts_local_resource_with_git() -> None:
    resource = require_worktree_parent(local_git_manifest(), "local")
    assert isinstance(resource, SymlinkResource)
    assert resource.git is not None


def test_require_worktree_parent_rejects_local_resource_without_git() -> None:
    with pytest.raises(ServiceError, match="worktree parent has no git declaration: local"):
        require_worktree_parent(Manifest.model_validate(manifest_data()), "local")


def test_require_worktree_parent_rejects_remote_resource_with_git() -> None:
    data = manifest_data()
    data["projects"][1]["resource"]["git"] = {"url": "git@example.com:remote.git"}
    with pytest.raises(ServiceError, match="not a local resource: remote"):
        require_worktree_parent(Manifest.model_validate(data), "remote")


@pytest.mark.parametrize(
    ("project", "message"),
    [
        ("missing", "unknown project: missing"),
        ("no-resource", "project has no resource: no-resource"),
    ],
)
def test_require_worktree_parent_rejects_unusable_project(
    project: str,
    message: str,
) -> None:
    with pytest.raises(ServiceError, match=message):
        require_worktree_parent(local_git_manifest(), project)
