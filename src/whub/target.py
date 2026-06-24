"""Target routing for project resources."""
from __future__ import annotations
from collections.abc import Callable
from typing import TypeVar, assert_never
import click
from whub.models import Manifest, RemoteResource, Resource, SymlinkResource

class TargetError(click.ClickException):
    pass

# return Resource Model (SymlinkResource / RemoteResource)
def resolve_target(manifest: Manifest, project_name: str) -> Resource:
    project = manifest.resolve_project(project_name)
    if project is None:
        raise TargetError(f"unknown project: {project_name}")
    if project.resource is None:
        raise TargetError(f"project has no resource: {project_name}")
    return project.resource


D = TypeVar("D")    # represents the data
R = TypeVar("R")    # represents the Resource

# exec function corresponding to the resource type
def on_target(
    target: Resource,
    data: D,
    *,
    local: Callable[[SymlinkResource, D], R],
    remote: Callable[[RemoteResource, D], R],
) -> R:
    if isinstance(target, SymlinkResource):
        return local(target, data)
    if isinstance(target, RemoteResource):
        return remote(target, data)
    assert_never(target)
