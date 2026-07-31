"""Task creation, reference resolution, and YAML persistence."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
import os
from pathlib import Path
import re
import tempfile

import yaml
from pydantic import ValidationError

from whub.core.health import probe_directory_readable
from whub.utils.apple_double import is_apple_double
from whub.wflow.models.task import TASK_ID_PATTERN, TaskDocument, TaskHeader
from whub.wflow.services.errors import WflowError


# yaml.safe_loadは純Python実装固定のため、libyaml版があれば明示的に使う
_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def load_task(path: Path) -> TaskDocument:
    if is_apple_double(path):
        raise WflowError(f"AppleDouble metadata is not a Task YAML: {path}")
    try:
        return TaskDocument.model_validate(
            yaml.load(path.read_text(), Loader=_SAFE_LOADER)
        )
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as error:
        raise WflowError(f"failed to load task YAML: {path}: {error}") from error


def iter_task_paths(root: Path) -> Iterator[Path]:
    """Yield Task YAML paths while excluding AppleDouble sidecars."""
    probe = probe_directory_readable(root)
    # timeoutは高遅延mountでも起きるため障害扱いせず続行（denied/errorのみ停止）
    if probe.outcome in ("denied", "error"):
        raise WflowError(
            f"task directory is unreadable: {root}: {probe.detail}; "
            "check filesystem permissions; for mounted resources, allow "
            "Network Volumes access for this app and remount"
        )
    return (path for path in root.rglob("*.yaml") if not is_apple_double(path))


def resolve_task_reference(reference: str, root: Path = Path(".")) -> Path:
    task_id = (
        reference
        if re.fullmatch(TASK_ID_PATTERN, reference)
        else f"TASK-{reference}"
        if re.fullmatch(r"[0-9]+", reference)
        else None
    )
    if task_id is None:
        return Path(reference)
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")
    matches = [
        path for path in sorted(iter_task_paths(root)) if _task_id(path) == task_id
    ]
    if not matches:
        raise WflowError(f"task ID not found: {task_id}")
    if len(matches) > 1:
        raise WflowError(
            f"task ID is ambiguous: {task_id}: {', '.join(map(str, matches))}"
        )
    return matches[0]


# TaskDocumentでTASK-IDを持つid keyはtask headerだけで、常にtop-level直下へ書き出される。
# ID照合のために全fileをYAML解析すると1件の解決に全件分のコストがかかるため、この行だけを拾う
_TASK_ID_LINE = re.compile(r"^  id: (TASK-[0-9]+)$", re.MULTILINE)


def _task_id(path: Path) -> str | None:
    try:
        text = path.read_text()
    except (OSError, UnicodeError):
        return None
    ids = _TASK_ID_LINE.findall(text)
    if len(ids) == 1:
        return ids[0]
    # 引用符付きやindent違いなど想定外の整形は、従来どおり全文解析で判定する
    try:
        return load_task(path).task.id
    except WflowError:
        return None


def create_task(
    root: Path,
    title: str,
    objective: str,
    approaches: tuple[str, ...] = (),
    now: datetime | None = None,
) -> tuple[Path, TaskDocument]:
    if root.exists() and not root.is_dir():
        raise WflowError(f"task path is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    numbers = [
        int(task_id.removeprefix("TASK-"))
        for path in iter_task_paths(root)
        if (task_id := _task_id(path)) is not None
    ]
    number = max(numbers, default=0) + 1
    try:
        task = TaskDocument(
            schema_version=1,
            task=TaskHeader(
                id=f"TASK-{number:03}",
                state="draft",
                title=title,
                objective=objective,
                approach=list(approaches),
            ),
        )
    except ValidationError as error:
        raise WflowError(f"invalid task input: {error}") from error
    path = root / f"{(now or datetime.now()):%Y%m%d_%H%M}_task-{number:03}.yaml"
    _write(path, task, create=True)
    return path, task


def write_task(path: Path, task: TaskDocument) -> None:
    _write(path, task, create=False)


def archive_task(path: Path, task: TaskDocument) -> Path:
    """Atomically place a completed Task beneath the sibling done directory."""
    if task.task.state != "completed":
        raise WflowError("only completed tasks can be archived")
    destination = path.parent / "done" / path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(
                yaml.safe_dump(
                    task.model_dump(mode="json"), allow_unicode=True, sort_keys=False
                )
            )
            temporary_path = Path(temporary.name)
        os.link(temporary_path, destination)
        path.unlink()
    except FileExistsError as error:
        raise WflowError(f"archived task already exists: {destination}") from error
    except OSError as error:
        raise WflowError(f"failed to archive task YAML: {path}: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return destination


def _write(path: Path, task: TaskDocument, create: bool) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(
                yaml.safe_dump(
                    task.model_dump(mode="json"), allow_unicode=True, sort_keys=False
                )
            )
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
