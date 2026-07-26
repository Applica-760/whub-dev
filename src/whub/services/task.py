"""Task operations shared by whub web adapters."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile

from whub.core.remote import build_remote_tar_command, run_ssh_command_bytes
from whub.models import Manifest, RemoteResource, SymlinkResource
from whub.services.errors import NotFoundError, ServiceError
from whub.services.project_content import (
    resolve_project_content_resource,
    resolve_project_content_root,
)
from whub.utils.process import format_process_error
from whub.wflow.models.task import TaskDocument, TaskSummary
from whub.wflow.services import (
    WflowError,
    list_tasks,
    load_task,
    load_task_workflow,
    render_task_flow,
    resolve_task_reference,
    validate_task,
)


TASKS_RELATIVE_PATH = Path("docs/tasks")

REMOTE_FETCH_TIMEOUT = 30


def resolve_project_task_root(manifest: Manifest, project: str) -> Path:
    """Resolve a local Project's standard Task directory."""
    task_root = resolve_project_content_root(manifest, project) / TASKS_RELATIVE_PATH
    if task_root.exists() and not task_root.is_dir():
        raise ServiceError(f"project task path is not a directory: {project}")
    return task_root


def _fetch_remote_task_root(
    resource: RemoteResource,
    project: str,
    destination: Path,
) -> Path | None:
    """Expand the remote Task directory below DESTINATION, or None when absent."""
    try:
        result = run_ssh_command_bytes(
            resource._resolved_host,
            build_remote_tar_command(
                resource.remote_path,
                TASKS_RELATIVE_PATH.as_posix(),
            ),
            batch_mode=True,
            connect_timeout=5,
            timeout=REMOTE_FETCH_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ServiceError(
            f"remote task read failed: {project}: {format_process_error(error)}"
        ) from error

    if result.returncode != 0:
        detail = (
            result.stderr.decode(errors="replace").strip()
            or f"exit status {result.returncode}"
        )
        raise ServiceError(f"remote task read failed: {project}: {detail}")
    if not result.stdout:
        return None

    try:
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
            archive.extractall(destination, filter="data")
    except (tarfile.TarError, OSError) as error:
        raise ServiceError(f"remote task read failed: {project}: {error}") from error
    return destination / TASKS_RELATIVE_PATH


@contextmanager
def project_task_root(manifest: Manifest, project: str) -> Iterator[Path | None]:
    """Yield a readable Task directory, or None when the Project has none.

    remote Projectはmountを走査せず、remote host上でtarを生成させて1往復で取得する。
    file数に比例するmount I/Oを避けるため、解析は展開後のローカルcopyへ行う。
    """
    resource = resolve_project_content_resource(manifest, project)
    if isinstance(resource, SymlinkResource):
        task_root = resolve_project_task_root(manifest, project)
        yield task_root if task_root.exists() else None
        return
    with tempfile.TemporaryDirectory(prefix="whub-tasks-") as directory:
        yield _fetch_remote_task_root(resource, project, Path(directory))


def list_project_tasks(
    manifest: Manifest,
    project: str,
) -> tuple[TaskSummary, ...]:
    """Return Task summaries from one Project, or an empty result when absent."""
    with project_task_root(manifest, project) as task_root:
        if task_root is None:
            return ()
        try:
            return list_tasks(task_root)
        except WflowError as error:
            raise ServiceError(str(error)) from error


@dataclass(frozen=True)
class ProjectTasks:
    """One Project's Task summaries, or the error that prevented reading them."""

    project: str
    tasks: tuple[TaskSummary, ...] = ()
    error: str | None = None


def list_all_project_tasks(manifest: Manifest) -> tuple[ProjectTasks, ...]:
    """Return every Project's Task summaries, isolating per-Project failures."""
    results: list[ProjectTasks] = []
    for project in manifest.projects:
        try:
            tasks = list_project_tasks(manifest, project.name)
        except (ServiceError, OSError) as error:
            results.append(ProjectTasks(project=project.name, error=str(error)))
            continue
        results.append(ProjectTasks(project=project.name, tasks=tasks))
    return tuple(results)


def load_project_task(
    manifest: Manifest,
    project: str,
    task_id: str,
) -> TaskDocument:
    """Load and validate one Task within one Project."""
    with project_task_root(manifest, project) as task_root:
        if task_root is None:
            raise NotFoundError(f"task not found: {project}/{task_id}")
        try:
            path = resolve_task_reference(task_id, task_root)
            document = load_task(path)
            diagnostics = validate_task(document, load_task_workflow())
        except WflowError as error:
            if str(error).startswith("task ID not found:"):
                raise NotFoundError(f"task not found: {project}/{task_id}") from error
            raise ServiceError(str(error)) from error
    if diagnostics:
        raise ServiceError(
            "task is invalid: " + "; ".join(item.message for item in diagnostics)
        )
    return document


def render_project_task_flow(
    manifest: Manifest,
    project: str,
    task_id: str,
) -> str:
    """Render one validated Project Task as Mermaid."""
    return render_task_flow(load_project_task(manifest, project, task_id))
