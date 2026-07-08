"""whub backlog — append a raw memo to a project's backlog."""
from __future__ import annotations
import shlex
import subprocess
from pathlib import Path
import click
from whub.commands import get_manifest
from whub.models import (
    Manifest,
    RemoteResource,
    SymlinkResource,
    project_names,
    workspace_hub_resource,
)
from whub.remote import run_ssh_command
from whub.target import TargetItem, on_targets, resolve_project_resource

_MARKER_START = "<!-- hub:backlog:appended:start -->"
_MARKER_END = "<!-- hub:backlog:appended:end -->"


def _seed(project_name: str) -> str:
    return (
        f"# {project_name} Backlog\n\n"
        f"{_MARKER_START}\n{_MARKER_END}\n"
    )


def _insert_memo(content: str, memo: str) -> str:
    if content.count(_MARKER_START) != 1 or content.count(_MARKER_END) != 1:
        raise click.ClickException("backlog markers are missing or duplicated")
    start, end = content.index(_MARKER_START), content.index(_MARKER_END)
    if start > end:
        raise click.ClickException("backlog start marker appears after end marker")
    return content[:end] + f"- {memo}\n" + content[end:]


def _resolve_target_resource(
    manifest: Manifest, project: str, data: tuple[str, str]
) -> TargetItem[tuple[str, str]]:
    proj = manifest.resolve_project(project)
    if proj is not None and proj.resource is None and proj.name == "workspace-hub":
        return TargetItem(workspace_hub_resource(), data)
    return TargetItem(resolve_project_resource(manifest, project), data)


def _local_backlog(resource: SymlinkResource, data: tuple[str, str]) -> None:
    name, memo = data
    root = Path(resource.source)
    if not root.exists():
        raise click.ClickException(f"resource source does not exist: {root}")
    path = root / "docs" / "backlog.md"
    content = path.read_text() if path.exists() else _seed(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_insert_memo(content, memo))
    click.echo(f"  backlog {name}: {memo}")


def _remote_backlog(resource: RemoteResource, data: tuple[str, str]) -> None:
    name, memo = data
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
            raise click.ClickException(
                f"remote resource path does not exist: {root}"
            )
        if root_check.returncode != 0:
            detail = (
                root_check.stderr.strip()
                or root_check.stdout.strip()
                or f"exit status {root_check.returncode}"
            )
            raise click.ClickException(f"remote backlog failed: {detail}")

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
            content = _seed(name)
        else:
            raise click.ClickException(f"unexpected remote backlog path: {path}")

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
        raise click.ClickException(f"remote backlog failed: {error}") from error
    click.echo(f"  backlog {name}: {memo}")


@click.command()
@click.argument("project", shell_complete=project_names)
@click.argument("text", nargs=-1, required=True)
@click.pass_context
def backlog(ctx: click.Context, project: str, text: tuple[str, ...]) -> None:
    """Append a raw memo to a project's backlog."""
    manifest = get_manifest(ctx)
    memo = " ".join(text).strip()
    if not memo:
        raise click.UsageError("memo text is required")
    target = _resolve_target_resource(manifest, project, (project, memo))
    on_targets([target], local=_local_backlog, remote=_remote_backlog)
