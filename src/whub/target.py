"""Target routing for project resources."""
from __future__ import annotations
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar, assert_never
import click
from whub.models import Manifest, RemoteResource, Resource, SymlinkResource

class TargetError(click.ClickException):
    pass


def resolve_target(manifest: Manifest, project_name: str) -> Resource:
    project = manifest.resolve_project(project_name)
    if project is None:
        raise TargetError(f"unknown project: {project_name}")
    if project.resource is None:
        raise TargetError(f"project has no resource: {project_name}")
    return project.resource


D = TypeVar("D")
R = TypeVar("R")

@dataclass(frozen=True)
class TargetItem(Generic[D]):
    resource: Resource
    data: D

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
