"""Task creation, reference resolution, and YAML persistence."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import tempfile

import yaml
from pydantic import ValidationError

from whub.wflow.models.task import TASK_ID_PATTERN, TaskDocument, TaskHeader
from whub.wflow.services.errors import WflowError


def load_task(path: Path) -> TaskDocument:
    try:
        return TaskDocument.model_validate(yaml.safe_load(path.read_text()))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise WflowError(f"failed to load task YAML: {path}: {error}") from error


def resolve_task_reference(reference: str, root: Path = Path("docs/tasks")) -> Path:
    import re
    task_id = reference if re.fullmatch(TASK_ID_PATTERN, reference) else f"TASK-{reference}" if re.fullmatch(r"[0-9]+", reference) else None
    if task_id is None:
        return Path(reference)
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")
    matches = [path for path in sorted(root.rglob("*.yaml")) if _task_id(path) == task_id]
    if not matches:
        raise WflowError(f"task ID not found: {task_id}")
    if len(matches) > 1:
        raise WflowError(f"task ID is ambiguous: {task_id}: {', '.join(map(str, matches))}")
    return matches[0]


def _task_id(path: Path) -> str | None:
    try:
        return load_task(path).task.id
    except WflowError:
        return None


def create_task(root: Path, title: str, objective: str, approaches: tuple[str, ...] = (), now: datetime | None = None) -> tuple[Path, TaskDocument]:
    if root.exists() and not root.is_dir():
        raise WflowError(f"task path is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    numbers = [int(task_id.removeprefix("TASK-")) for path in root.rglob("*.yaml") if (task_id := _task_id(path)) is not None]
    number = max(numbers, default=0) + 1
    task = TaskDocument(schema_version=1, task=TaskHeader(id=f"TASK-{number:03}", state="draft", title=title, objective=objective, approach=list(approaches)))
    path = root / f"{(now or datetime.now()):%Y%m%d_%H%M}_task-{number:03}.yaml"
    _write(path, task, create=True)
    return path, task


def write_task(path: Path, task: TaskDocument) -> None:
    _write(path, task, create=False)


def _write(path: Path, task: TaskDocument, create: bool) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as temporary:
            temporary.write(yaml.safe_dump(task.model_dump(mode="json"), allow_unicode=True, sort_keys=False))
            temporary_path = Path(temporary.name)
        if create:
            os.link(temporary_path, path)
        else:
            os.replace(temporary_path, path)
    except FileExistsError as error:
        raise WflowError(f"task path already exists: {path}") from error
    except OSError as error:
        raise WflowError(f"failed to write task YAML: {path}: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
