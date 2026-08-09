"""Task runtime dependency and interruption operations."""

from __future__ import annotations

from collections.abc import Mapping

from whub.models.flow import TaskRuntime, WorkflowDefinition
from whub.services.flow.errors import Diagnostic, FlowError
from whub.services.flow.task.eligibility import (
    interruption_resume_diagnostics,
    interruption_start_diagnostics,
)
from whub.services.flow.task.integrity import validate_task_set
from whub.services.flow.task.transition import apply_transition


def update_dependency(task: TaskRuntime, dependency: str, add: bool) -> TaskRuntime:
    if task.state != "draft":
        raise FlowError("dependency operations require a draft task")
    if dependency == task.id:
        raise FlowError("task cannot depend on itself")
    dependencies = list(task.depends_on)
    if add:
        if dependency in dependencies:
            raise FlowError(f"dependency already exists: {dependency}")
        dependencies.append(dependency)
    else:
        if dependency not in dependencies:
            raise FlowError(f"dependency not found: {dependency}")
        dependencies.remove(dependency)
    return TaskRuntime.model_validate(
        {**task.model_dump(mode="python"), "depends_on": dependencies}
    )


def _require_no_diagnostics(diagnostics: tuple[tuple[str, Diagnostic], ...]) -> None:
    if diagnostics:
        details = "; ".join(
            f"{task_id}: {item.message}" for task_id, item in diagnostics
        )
        raise FlowError(f"task interruption is invalid: {details}")


def interrupt_task(
    parent: TaskRuntime,
    child: TaskRuntime,
    tasks: Mapping[str, TaskRuntime],
    workflow: WorkflowDefinition,
    reason: str,
) -> tuple[TaskRuntime, TaskRuntime]:
    _require_no_diagnostics(
        interruption_start_diagnostics(parent, child, tasks, workflow, reason)
    )
    paused_parent = apply_transition(
        parent.model_copy(update={"interruption_task_id": child.id}),
        workflow,
        "interrupt_task",
    )
    started_child = child.model_copy(update={"interruption_source_task_id": parent.id})
    if started_child.state == "draft":
        started_child = apply_transition(started_child, workflow, "start_task")
    _require_no_diagnostics(
        validate_task_set(
            {**tasks, paused_parent.id: paused_parent, started_child.id: started_child},
            workflow,
        )
    )
    return paused_parent, started_child


def resume_task(
    parent: TaskRuntime, tasks: Mapping[str, TaskRuntime], workflow: WorkflowDefinition
) -> TaskRuntime:
    _require_no_diagnostics(interruption_resume_diagnostics(parent, tasks, workflow))
    resumed = apply_transition(parent, workflow, "resume_task")
    _require_no_diagnostics(validate_task_set({**tasks, resumed.id: resumed}, workflow))
    return resumed
