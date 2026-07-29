"""Task dependency and interruption relation operations."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import ValidationError

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import Diagnostic, WflowError
from whub.wflow.services.task.eligibility import (
    interruption_resume_diagnostics,
    interruption_start_diagnostics,
)
from whub.wflow.services.task.integrity import (
    validate_task_set,
)
from whub.wflow.services.task.transition import apply_transition


def update_dependency(
    task: TaskDocument,
    dependency: str,
    add: bool,
) -> TaskDocument:
    """Add or remove one Task dependency while the Task is draft."""
    if task.task.state != "draft":
        raise WflowError("dependency operations require a draft task")
    if dependency == task.task.id:
        raise WflowError("task cannot depend on itself")
    data = task.model_dump(mode="python")
    dependencies = data["task"]["depends_on"]
    if add:
        if dependency in dependencies:
            raise WflowError(f"dependency already exists: {dependency}")
        dependencies.append(dependency)
    else:
        if dependency not in dependencies:
            raise WflowError(f"dependency not found: {dependency}")
        dependencies.remove(dependency)
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(
            f"failed to update dependency '{dependency}': {error}"
        ) from error


def _require_no_diagnostics(diagnostics: tuple[tuple[str, Diagnostic], ...]) -> None:
    if diagnostics:
        details = "; ".join(
            f"{task_id}: {item.message}" for task_id, item in diagnostics
        )
        raise WflowError(f"task interruption is invalid: {details}")


def interrupt_task(
    parent: TaskDocument,
    child: TaskDocument,
    tasks: Mapping[str, TaskDocument],
    workflow: WorkflowDefinition,
    reason: str,
) -> tuple[TaskDocument, TaskDocument]:
    """Freeze PARENT and start CHILD as one validated interruption."""
    _require_no_diagnostics(
        interruption_start_diagnostics(parent, child, tasks, workflow, reason)
    )

    parent_data = parent.model_dump(mode="python")
    parent_data["task"]["interruption_task_id"] = child.task.id
    parent_data["task"]["interruption_reason"] = reason
    paused_parent = apply_transition(
        TaskDocument.model_validate(parent_data), workflow, "interrupt_task", "agent"
    )

    child_data = child.model_dump(mode="python")
    child_data["task"]["interruption_source_task_id"] = parent.task.id
    if child.task.state == "draft":
        child_data["task"]["state"] = "in_progress"
        child_data["approvals"].append({"actor": "user"})
    started_child = TaskDocument.model_validate(child_data)

    _require_no_diagnostics(
        validate_task_set(
            {
                **tasks,
                paused_parent.task.id: paused_parent,
                started_child.task.id: started_child,
            },
            workflow,
        )
    )
    return paused_parent, started_child


def resume_task(
    parent: TaskDocument,
    tasks: Mapping[str, TaskDocument],
    workflow: WorkflowDefinition,
) -> TaskDocument:
    """Resume PARENT only after its interruption Task is terminal."""
    _require_no_diagnostics(interruption_resume_diagnostics(parent, tasks, workflow))
    resumed = apply_transition(parent, workflow, "resume_task", "agent")
    _require_no_diagnostics(
        validate_task_set({**tasks, resumed.task.id: resumed}, workflow)
    )
    return resumed
