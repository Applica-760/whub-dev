"""Task runtime YAML persistence."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
import os
from pathlib import Path
import tempfile

import yaml
from pydantic import ValidationError

from whub.models.flow import TaskRuntime
from whub.services.flow.errors import FlowError
from whub.utils.apple_double import is_apple_double


_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def load_task(path: Path) -> TaskRuntime:
    if is_apple_double(path):
        raise FlowError(f"AppleDouble metadata is not a Task YAML: {path}")
    try:
        return TaskRuntime.model_validate(
            yaml.load(path.read_text(), Loader=_SAFE_LOADER)
        )
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as error:
        raise FlowError(f"failed to load task YAML: {path}: {error}") from error


def iter_task_paths(root: Path) -> Iterator[Path]:
    return (path for path in root.rglob("*.yaml") if not is_apple_double(path))


def write_task(path: Path, task: TaskRuntime) -> None:
    try:
        _write_text(path, _task_yaml(task))
    except OSError as error:
        raise FlowError(f"failed to write task YAML: {path}: {error}") from error


def write_task_set(tasks: dict[Path, TaskRuntime]) -> None:
    """Write related runtime YAML files, restoring earlier writes on failure."""
    previous: dict[Path, str] = {}
    written: list[Path] = []
    try:
        for path, task in tasks.items():
            previous[path] = path.read_text(encoding="utf-8")
            _write_text(path, _task_yaml(task))
            written.append(path)
    except (OSError, UnicodeError) as error:
        for path in written:
            _write_text(path, previous[path])
        raise FlowError(f"failed to write Task runtime set: {error}") from error


def task_markdown_path(task_path: Path) -> Path:
    if task_path.suffix != ".yaml":
        raise FlowError(f"task path must end in .yaml: {task_path}")
    return task_path.with_suffix(".md")


def load_task_markdown(task_path: Path) -> str:
    path = task_markdown_path(task_path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise FlowError(f"failed to load task Markdown: {path}: {error}") from error


def write_task_markdown(task_path: Path, content: str) -> Path:
    path = task_markdown_path(task_path)
    try:
        _write_text(path, content)
    except (OSError, UnicodeError) as error:
        raise FlowError(f"failed to write task Markdown: {path}: {error}") from error
    return path


def create_task(
    root: Path,
    title: str,
    objective: str,
    approaches: tuple[str, ...] = (),
    now: datetime | None = None,
    id_roots: tuple[Path, ...] = (),
) -> tuple[Path, TaskRuntime]:
    if root.exists() and not root.is_dir():
        raise FlowError(f"task path is not a directory: {root}")
    if (
        not title.strip()
        or not objective.strip()
        or any(not item.strip() for item in approaches)
    ):
        raise FlowError("task title, objective, and approaches must be non-empty")
    root.mkdir(parents=True, exist_ok=True)
    numbers = [
        int(task_id.removeprefix("TASK-"))
        for task_root in (root, *id_roots)
        for candidate in iter_task_paths(task_root)
        if (task_id := _task_id(candidate)) is not None
    ]
    number = max(numbers, default=0) + 1
    task = TaskRuntime(
        schema_version=2,
        id=f"TASK-{number:03}",
        workflow="WF-001",
        state="draft",
    )
    path = root / f"{(now or datetime.now()):%Y%m%d_%H%M}_task-{number:03}.yaml"
    try:
        _create_files(
            (path, _task_yaml(task)),
            (task_markdown_path(path), _task_markdown(title, objective, approaches)),
        )
    except FileExistsError as error:
        raise FlowError(f"task path already exists: {error.filename}") from error
    except OSError as error:
        raise FlowError(f"failed to create task pair: {path}: {error}") from error
    return path, task


def archive_task(path: Path, task: TaskRuntime, destination_root: Path) -> Path:
    """Move a terminal Task YAML and its Markdown sibling as one pair."""
    if task.state not in {"completed", "cancelled"}:
        raise FlowError("only terminal tasks can be archived")
    source_markdown = task_markdown_path(path)
    destination = destination_root / path.name
    destination_markdown = task_markdown_path(destination)
    try:
        source_yaml_content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise FlowError(f"failed to archive task YAML: {path}: {error}") from error
    yaml_content = _task_yaml(task)
    try:
        markdown_content = source_markdown.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise FlowError(
            f"failed to archive task Markdown: {source_markdown}: {error}"
        ) from error

    removed_yaml = False
    removed_markdown = False
    destination_created = False
    try:
        destination_root.mkdir(parents=True, exist_ok=True)
        _create_files(
            (destination, yaml_content),
            (destination_markdown, markdown_content),
        )
        destination_created = True
        path.unlink()
        removed_yaml = True
        source_markdown.unlink()
        removed_markdown = True
    except FileExistsError as error:
        raise FlowError(f"archived task already exists: {error.filename}") from error
    except OSError as error:
        raise FlowError(f"failed to archive task pair: {path}: {error}") from error
    finally:
        if removed_yaml != removed_markdown:
            if removed_yaml:
                _write_text(path, source_yaml_content)
            if removed_markdown:
                _write_text(source_markdown, markdown_content)
        if destination_created and not (removed_yaml and removed_markdown):
            for created_path in (destination, destination_markdown):
                created_path.unlink(missing_ok=True)
    return destination


def _task_yaml(task: TaskRuntime) -> str:
    return yaml.safe_dump(
        task.model_dump(mode="json"), allow_unicode=True, sort_keys=False
    )


def _task_markdown(title: str, objective: str, approaches: tuple[str, ...]) -> str:
    sections = [f"# {title.strip()}", f"## Objective\n\n{objective.strip()}"]
    if approaches:
        sections.append(
            "## Approach\n\n" + "\n".join(f"- {item.strip()}" for item in approaches)
        )
    return "\n\n".join(sections) + "\n"


def _write_text(path: Path, content: str) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _create_files(*files: tuple[Path, str]) -> None:
    temporary_paths: list[Path] = []
    created_paths: list[Path] = []
    try:
        for path, content in files:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, delete=False
            ) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            temporary_paths.append(temporary_path)
            os.link(temporary_path, path)
            created_paths.append(path)
    except OSError:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)


def _task_id(path: Path) -> str | None:
    try:
        return load_task(path).id
    except FlowError:
        return None
