"""Target routing for project resources."""
from __future__ import annotations
from collections.abc import Callable, Iterable
from typing import TypeVar, assert_never
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

def on_targets(
    targets: Iterable[tuple[Resource, D]],
    *,
    local: Callable[[SymlinkResource, D], R],
    remote: Callable[[RemoteResource, D], R],
) -> list[R]:
    results: list[R] = []
    for target, data in targets:
        if isinstance(target, SymlinkResource):
            results.append(local(target, data))
        elif isinstance(target, RemoteResource):
            results.append(remote(target, data))
        else:
            assert_never(target)
    return results
