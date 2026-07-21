"""Backlog operations shared by CLI and web adapters."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from whub.models import Manifest, RemoteResource, SymlinkResource
from whub.core.remote import run_ssh_command
from whub.services.errors import ServiceError
from whub.services.project_content import resolve_project_content_resource
from whub.core.target import TargetItem, on_targets
from whub.utils.managed_block import format_block, insert_before_end_marker
from whub.utils.process import format_process_error

MARKERS = ("<!-- hub:backlog:appended:start -->", "<!-- hub:backlog:appended:end -->")


def _insert_memo(content: str, memo: str) -> str:
    if content.count(MARKERS[0]) != 1 or content.count(MARKERS[1]) != 1:
        raise ServiceError("backlog markers are missing or duplicated")
    if content.index(MARKERS[0]) > content.index(MARKERS[1]):
        raise ServiceError("backlog start marker appears after end marker")
    return insert_before_end_marker(content, f"- {memo}\n", MARKERS)


def _append_local_backlog(
    resource: SymlinkResource,
    memo: str,
) -> None:
    root = Path(resource.source)
    if not root.exists():
        raise ServiceError(f"resource source does not exist: {root}")
    path = root / "docs" / "backlog.md"
    content = path.read_text() if path.exists() else format_block(MARKERS, "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_insert_memo(content, memo))


def _append_remote_backlog(
    resource: RemoteResource,
    memo: str,
) -> None:
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
    target = TargetItem(resolve_project_content_resource(manifest, project), memo)
    on_targets(
        [target],
        local=_append_local_backlog,
        remote=_append_remote_backlog,
    )


def _read_local_backlog(resource: SymlinkResource, data: None) -> str:
    del data
    root = Path(resource.source)
    if not root.is_dir():
        raise ServiceError(f"resource source does not exist: {root}")
    path = root / "docs" / "backlog.md"
    if not path.exists():
        return ""
    if not path.is_file():
        raise ServiceError(f"unexpected backlog path: {path}")
    return path.read_text()


def _read_remote_backlog(resource: RemoteResource, data: None) -> str:
    del data
    root = resource._resolved_workspace_path
    if not root.is_dir():
        raise ServiceError(f"remote workspace path is not available: {root}")
    path = root / "docs" / "backlog.md"
    if not path.exists():
        return ""
    if not path.is_file():
        raise ServiceError(f"unexpected backlog path: {path}")
    return path.read_text()


def read_backlog(manifest: Manifest, project: str) -> str:
    """Return PROJECT's local or mounted backlog content."""
    target = TargetItem(resolve_project_content_resource(manifest, project), None)
    return on_targets(
        [target],
        local=_read_local_backlog,
        remote=_read_remote_backlog,
    )[0]
