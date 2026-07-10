"""Backlog operations shared by CLI and web adapters."""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from whub.models import Manifest, RemoteResource, SymlinkResource, workspace_hub_resource
from whub.remote import run_ssh_command
from whub.services.errors import ServiceError
from whub.target import TargetItem, on_targets
from whub.utils.managed_block import format_block, insert_before_end_marker
from whub.utils.process import format_process_error

MARKERS = ("<!-- hub:backlog:appended:start -->", "<!-- hub:backlog:appended:end -->")


def _insert_memo(content: str, memo: str) -> str:
    if content.count(MARKERS[0]) != 1 or content.count(MARKERS[1]) != 1:
        raise ServiceError("backlog markers are missing or duplicated")
    if content.index(MARKERS[0]) > content.index(MARKERS[1]):
        raise ServiceError("backlog start marker appears after end marker")
    return insert_before_end_marker(content, f"- {memo}\n", MARKERS)


def _resolve_target_resource(
    manifest: Manifest,
    project: str,
    memo: str,
) -> TargetItem[tuple[str, str]]:
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    if resolved_project.resource is None:
        if resolved_project.name == "workspace-hub":
            return TargetItem(workspace_hub_resource(), (project, memo))
        raise ServiceError(f"project has no resource: {project}")
    return TargetItem(resolved_project.resource, (project, memo))


def _append_local_backlog(
    resource: SymlinkResource,
    data: tuple[str, str],
) -> None:
    _, memo = data
    root = Path(resource.source)
    if not root.exists():
        raise ServiceError(f"resource source does not exist: {root}")
    path = root / "docs" / "backlog.md"
    content = path.read_text() if path.exists() else format_block(MARKERS, "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_insert_memo(content, memo))


def _append_remote_backlog(
    resource: RemoteResource,
    data: tuple[str, str],
) -> None:
    _, memo = data
    host = resource._resolved_host
    root = resource.path
    docs = f"{root}/docs"
    path = f"{docs}/backlog.md"

    try:
        root_check = run_ssh_command(
            host,
            f"test -d {shlex.quote(root)}",
            timeout=10,
            batch_mode=True,
            connect_timeout=5,
        )
        if root_check.returncode == 1:
            raise ServiceError(f"remote resource path does not exist: {root}")
        if root_check.returncode != 0:
            detail = (
                root_check.stderr.strip()
                or root_check.stdout.strip()
                or f"exit status {root_check.returncode}"
            )
            raise ServiceError(f"remote backlog failed: {detail}")

        state = run_ssh_command(
            host,
            (
                f"if test -f {shlex.quote(path)}; then echo file; "
                f"elif test -e {shlex.quote(path)}; then echo unexpected; "
                "else echo missing; fi"
            ),
            timeout=10,
            batch_mode=True,
            connect_timeout=5,
            check=True,
        ).stdout.strip()

        if state == "file":
            content = run_ssh_command(
                host,
                f"cat {shlex.quote(path)}",
                timeout=30,
                batch_mode=True,
                connect_timeout=5,
                check=True,
            ).stdout
        elif state == "missing":
            content = format_block(MARKERS, "")
        else:
            raise ServiceError(f"unexpected remote backlog path: {path}")

        run_ssh_command(
            host,
            f"mkdir -p {shlex.quote(docs)} && cat > {shlex.quote(path)}",
            input=_insert_memo(content, memo),
            timeout=30,
            batch_mode=True,
            connect_timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ServiceError(
            f"remote backlog failed: {format_process_error(error)}"
        ) from error


def append_backlog(manifest: Manifest, project: str, memo: str) -> None:
    """Append MEMO to PROJECT's local or remote backlog."""
    target = _resolve_target_resource(manifest, project, memo)
    on_targets(
        [target],
        local=_append_local_backlog,
        remote=_append_remote_backlog,
    )
