"""Read and derive views from Task execution records."""
from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path
import re

import yaml
from pydantic import ValidationError

from whub.wflow.models.task import TASK_ID_PATTERN, TaskDocument, TaskSummary
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task_validation import validate_task
from whub.wflow.services.workflow import load_workflow


def load_task(path: Path) -> TaskDocument:
    """Load one task execution record from YAML."""
    try:
        return TaskDocument.model_validate(yaml.safe_load(path.read_text()))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise WflowError(f"failed to load task YAML: {path}: {error}") from error


def resolve_task_reference(
    reference: str,
    root: Path = Path("docs/tasks"),
) -> Path:
    """Resolve a Task ID or its numeric part in ROOT, or a YAML path."""
    task_id = (
        reference
        if re.fullmatch(TASK_ID_PATTERN, reference) is not None
        else f"TASK-{reference}" if re.fullmatch(r"[0-9]+", reference) else None
    )
    if task_id is None:
        return Path(reference)
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")

    matches: list[Path] = []
    for path in sorted(root.rglob("*.yaml")):
        try:
            if load_task(path).task.id == task_id:
                matches.append(path)
        except WflowError:
            continue
    if not matches:
        raise WflowError(f"task ID not found: {task_id}")
    if len(matches) > 1:
        paths = ", ".join(str(path) for path in matches)
        raise WflowError(f"task ID is ambiguous: {task_id}: {paths}")
    return matches[0]


def load_task_workflow() -> WorkflowDefinition:
    """Load the built-in Workflow definition for task records."""
    resource = files("whub.wflow.definitions").joinpath("task.yaml")
    with as_file(resource) as path:
        return load_workflow(path)


def list_tasks(root: Path) -> tuple[TaskSummary, ...]:
    """Discover Task YAML files below ROOT and derive their dependency status."""
    if not root.is_dir():
        raise WflowError(f"task directory does not exist: {root}")

    workflow = load_task_workflow()
    summaries: list[TaskSummary] = []
    for path in sorted(root.rglob("*.yaml")):
        relative_path = path.relative_to(root).as_posix()
        try:
            record = load_task(path)
        except WflowError as error:
            summaries.append(
                TaskSummary(
                    path=relative_path,
                    diagnostics=[" ".join(str(error).splitlines())],
                )
            )
            continue

        diagnostics = [
            f"{item.code}: {item.message}" for item in validate_task(record, workflow)
        ]
        summaries.append(
            TaskSummary(
                path=relative_path,
                id=record.task.id,
                title=record.task.title,
                state=record.task.state,
                depends_on=record.task.depends_on,
                diagnostics=diagnostics,
            )
        )
    ids: dict[str, list[TaskSummary]] = {}
    for summary in summaries:
        if summary.id is not None and not summary.diagnostics:
            ids.setdefault(summary.id, []).append(summary)
    duplicate_ids = {task_id for task_id, items in ids.items() if len(items) > 1}

    updated: list[TaskSummary] = []
    for summary in summaries:
        diagnostics = list(summary.diagnostics)
        if summary.id in duplicate_ids:
            diagnostics.append(f"duplicate task id: {summary.id}")
        if diagnostics:
            updated.append(summary.model_copy(update={"diagnostics": diagnostics}))
            continue

        blockers: list[str] = []
        for dependency in summary.depends_on:
            targets = ids.get(dependency, [])
            if not targets:
                blockers.append(f"missing dependency: {dependency}")
            elif dependency in duplicate_ids:
                blockers.append(f"ambiguous dependency: {dependency}")
            elif targets[0].state != "completed":
                blockers.append(
                    f"incomplete dependency: {dependency} ({targets[0].state})"
                )
        updated.append(
            summary.model_copy(
                update={
                    "blocked_by": blockers,
                    "ready": summary.state == "draft" and not blockers,
                }
            )
        )
    return tuple(updated)


def render_task_dependency_graph(root: Path) -> str:
    """Render valid Tasks below ROOT and their dependencies as Mermaid."""
    tasks = [
        item for item in list_tasks(root) if item.id is not None and not item.diagnostics
    ]
    lines = ["flowchart TD"]
    for item in tasks:
        lines.append(f'  {_mermaid_id(item.id)}["{_mermaid_label(item.id, item.title)}"]')
    for item in tasks:
        for dependency in item.depends_on:
            lines.append(f"  {_mermaid_id(dependency)} --> {_mermaid_id(item.id)}")
    return "\n".join(lines)


def render_task_flow(task: TaskDocument) -> str:
    """Render one Task's Phase order and Phase acceptance criteria as Mermaid."""
    lines = ["flowchart TD"]
    if task.plan is None:
        return "\n".join(lines)

    phase_ids: list[str] = []
    for phase_number, phase in enumerate(task.plan.phases, start=1):
        phase_id = f"phase_{phase_number:03}"
        phase_ids.append(phase_id)
        lines.append(
            f'  {phase_id}["{_mermaid_label(f"Phase {phase_number}", phase.title)}"]'
        )
        for criterion in phase.acceptance:
            acceptance_id = f"{phase_id}_{_mermaid_id(criterion.id)}"
            lines.append(
                f'  {acceptance_id}["{_mermaid_label(criterion.id, criterion.statement)}"]'
            )
            lines.append(f"  {phase_id} --> {acceptance_id}")
    lines.extend(
        f"  {source} --> {target}" for source, target in zip(phase_ids, phase_ids[1:])
    )
    if phase_ids:
        for criterion in task.plan.acceptance:
            acceptance_id = f"task_{_mermaid_id(criterion.id)}"
            lines.append(
                f'  {acceptance_id}["{_mermaid_label(criterion.id, criterion.statement)}"]'
            )
            lines.append(f"  {phase_ids[-1]} --> {acceptance_id}")
    return "\n".join(lines)


def _mermaid_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _mermaid_label(identifier: str, text: str | None) -> str:
    label = identifier if text is None else f"{identifier}: {text}"
    return label.replace('"', "&quot;").replace("\n", " ")
