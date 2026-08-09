"""Task runtime YAML persistence."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import re
import tempfile

import yaml
from pydantic import ValidationError

from whub.models.flow import TASK_ID_PATTERN, TaskRuntime
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


def resolve_task_reference(reference: str, root: Path) -> Path:
    task_id = (
        reference if re.fullmatch(TASK_ID_PATTERN, reference) else f"TASK-{reference}"
    )
    matches = [
        path for path in sorted(iter_task_paths(root)) if _task_id(path) == task_id
    ]
    if not matches:
        raise FlowError(f"task ID not found: {task_id}")
    if len(matches) > 1:
        raise FlowError(
            f"task ID is ambiguous: {task_id}: {', '.join(map(str, matches))}"
        )
    return matches[0]


def write_task(path: Path, task: TaskRuntime) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary:
            yaml.safe_dump(
                task.model_dump(mode="json"),
                temporary,
                allow_unicode=True,
                sort_keys=False,
            )
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    except OSError as error:
        raise FlowError(f"failed to write task YAML: {path}: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


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
        path.write_text(content, encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise FlowError(f"failed to write task Markdown: {path}: {error}") from error
    return path


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
    yaml_content = yaml.safe_dump(
        task.model_dump(mode="json"), allow_unicode=True, sort_keys=False
    )
    try:
        markdown_content = source_markdown.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise FlowError(
            f"failed to archive task Markdown: {source_markdown}: {error}"
        ) from error

    temporary_paths: list[Path] = []
    created_paths: list[Path] = []
    removed_yaml = False
    removed_markdown = False
    try:
        destination_root.mkdir(parents=True, exist_ok=True)
        for target, content in (
            (destination, yaml_content),
            (destination_markdown, markdown_content),
        ):
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=destination_root, delete=False
            ) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
            temporary_paths.append(temporary_path)
            os.link(temporary_path, target)
            created_paths.append(target)
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
                path.write_text(source_yaml_content, encoding="utf-8")
            if removed_markdown:
                source_markdown.write_text(markdown_content, encoding="utf-8")
        if removed_yaml != removed_markdown or not (removed_yaml and removed_markdown):
            for created_path in created_paths:
                created_path.unlink(missing_ok=True)
        for temporary_path in temporary_paths:
            temporary_path.unlink(missing_ok=True)
    return destination


def _task_id(path: Path) -> str | None:
    try:
        return load_task(path).id
    except FlowError:
        return None
