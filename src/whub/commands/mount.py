"""whub mount / unmount — sshfs-based mounts for remote resources."""
from __future__ import annotations
import shutil
import subprocess
import time
import click
from whub.commands import get_manifest
from whub.health import inspect_mount
from whub.models import Manifest, Project, RemoteResource, project_names
from whub.remote import build_sshfs_command


def _select_targets(
    m: Manifest,
    name: str | None,
    *,
    auto_only: bool = False,
) -> list[tuple[Project, RemoteResource]]:
    if name is not None:
        # 名指しは明示された意図なのでmountフラグを無視する
        project = m.resolve_project(name)
        if project is None:
            raise click.ClickException(f"unknown project: {name}")
        if not isinstance(project.resource, RemoteResource):
            raise click.ClickException(f"not a remote resource: {name}")
        return [(project, project.resource)]
    return [
        (project, project.resource)
        for project in m.projects
        if isinstance(project.resource, RemoteResource)
        and (not auto_only or project.resource.mount)
    ]


def _mount(project: Project, resource: RemoteResource) -> str:
    mountpoint = resource._resolved_workspace_path
    host = resource._resolved_host
    if mountpoint is None or host is None:
        return "FAIL: resource is unresolved"
    health = inspect_mount(resource)
    if health.state == "ok":
        return "skip"
    if health.state == "stale":
        return "STALE: run `whub unmount --force` first"

    mountpoint.mkdir(parents=True, exist_ok=True)
    cmd = build_sshfs_command(
        host, resource.path, mountpoint, volname=f"whub-{project.name}",
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"FAIL: {result.stderr.strip()}"
    # fuse-t on macOS: mount table lags ~0.2-0.4s behind sshfs exit
    for _ in range(10):
        health = inspect_mount(resource)
        if health.state == "ok":
            return "mount"
        time.sleep(0.2)
    return f"FAIL: {health.state}"


def _unmount(resource: RemoteResource, force: bool) -> str:
    mountpoint = resource._resolved_workspace_path
    if mountpoint is None:
        return "FAIL: resource is unresolved"
    health = inspect_mount(resource)
    if health.state == "unmounted":
        return "skip"
    if health.state == "stale" and not force:
        return "STALE: retry with --force"

    cmd = ["umount", *(["-f"] if force else []), str(mountpoint)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and force:
        result = subprocess.run(
            ["diskutil", "unmount", "force", str(mountpoint)],
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        return f"FAIL: {result.stderr.strip()}"
    if inspect_mount(resource).state == "unmounted":
        return "unmount"
    return "FAIL: still mounted"


def _echo_results(results: list[tuple[str, str]]) -> None:
    ok_statuses = ("mount", "unmount", "skip")
    for name, status in results:
        click.echo(f"  {status:6s}  {name}")
    if not results:
        click.echo("  (no remote resources)")
    if any(status not in ok_statuses for _, status in results):
        raise click.exceptions.Exit(1)


@click.command()
@click.argument("project", required=False, shell_complete=project_names)
@click.option("--all", "-a", "include_all", is_flag=True, help="Include resources with mount=false.")
@click.pass_context
def mount(ctx: click.Context, project: str | None, include_all: bool) -> None:
    """Mount remote resources via sshfs."""
    if shutil.which("sshfs") is None:
        raise click.ClickException("sshfs not found (brew install fuse-t sshfs-fuse-t)")
    m = get_manifest(ctx)
    targets = _select_targets(m, project, auto_only=not include_all)
    _echo_results([(p.name, _mount(p, r)) for p, r in targets])


@click.command()
@click.argument("project", required=False, shell_complete=project_names)
@click.option("--force", is_flag=True, help="Force unmount (for stale mounts).")
@click.pass_context
def unmount(ctx: click.Context, project: str | None, force: bool) -> None:
    """Unmount remote resources."""
    m = get_manifest(ctx)
    targets = _select_targets(m, project)
    _echo_results([(p.name, _unmount(r, force)) for p, r in targets])
