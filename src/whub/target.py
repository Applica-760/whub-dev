"""Target routing for project resources."""
from __future__ import annotations
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Generic, TypeVar, assert_never
import click
from whub.models import Manifest, Project, RemoteResource, Resource, SymlinkResource

class TargetError(click.ClickException):
    pass

def resolve_project_resource(manifest: Manifest, project_name: str) -> Resource:
    project = manifest.resolve_project(project_name)
    if project is None:
        raise TargetError(f"unknown project: {project_name}")
    if project.resource is None:
        raise TargetError(f"project has no resource: {project_name}")
    return project.resource


# workspace-hub相対パスから、それを含むresourceとresource内相対パスを解決
def resolve_resource_by_workspace_path(
    manifest: Manifest,
    path: str,
) -> tuple[Project, Resource, str]:
    parts = PurePosixPath(path).parts
    if PurePosixPath(path).is_absolute() or ".." in parts:
        raise TargetError(f"path must be relative to the workspace root: {path}")

    best: tuple[Project, Resource] | None = None
    best_depth = -1
    for project in manifest.projects:
        resource = project.resource
        if resource is None:
            continue
        base = PurePosixPath(resource.workspace_path).parts
        if parts[: len(base)] == base and len(base) > best_depth:
            best = (project, resource)
            best_depth = len(base)
    if best is None:
        raise TargetError(f"no resource contains path: {path}")

    project, resource = best
    return project, resource, "/".join(parts[best_depth:])


ResourceT = TypeVar("ResourceT", bound=Resource)

def require_resource_type(
    resource: Resource,
    expected: type[ResourceT],
    name: str,
) -> ResourceT:
    if isinstance(resource, expected):
        return resource
    label = (
        "remote" if expected is RemoteResource
        else "symlink" if expected is SymlinkResource
        else expected.__name__
    )
    raise TargetError(f"not a {label} resource: {name}")


D = TypeVar("D")
R = TypeVar("R")

@dataclass(frozen=True)
class TargetItem(Generic[D]):
    resource: Resource
    data: D

# resourceを持つprojectのTargetItemをreturn
def collect_targets(manifest: Manifest) -> list[TargetItem[Project]]:
    return [
        TargetItem(project.resource, project)
        for project in manifest.projects
        if project.resource is not None
    ]

# Resource種別により異なる関数を実行
def on_targets(
    targets: Iterable[TargetItem[D]],
    *,
    local: Callable[[SymlinkResource, D], R],
    remote: Callable[[RemoteResource, D], R],
) -> list[R]:
    results: list[R] = []
    for target in targets:
        resource = target.resource
        if isinstance(resource, SymlinkResource):
            results.append(local(resource, target.data))
        elif isinstance(resource, RemoteResource):
            results.append(remote(resource, target.data))
        else:
            assert_never(resource)
    return results
