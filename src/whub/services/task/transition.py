"""Task runtime lifecycle transitions."""

from __future__ import annotations

from typing import Any

from whub.models.flow import TaskRuntime, WorkflowDefinition
from whub.services.flow.errors import FlowError
from whub.services.task.integrity import validate_task
from whub.services.flow.workflow import apply_transition as apply_workflow_transition


def apply_transition(
    task: TaskRuntime,
    workflow: WorkflowDefinition,
    trigger: str,
    input_data: dict[str, Any] | None = None,
) -> TaskRuntime:
    if diagnostics := validate_task(task, workflow):
        raise FlowError(
            "task is invalid: " + "; ".join(item.message for item in diagnostics)
        )
    state, data = apply_workflow_transition(
        workflow,
        task.state,
        task.model_dump(mode="python"),
        trigger,
        "user",
        input_data,
    )
    data["state"] = state
    updated = TaskRuntime.model_validate(data)
    if diagnostics := validate_task(updated, workflow):
        raise FlowError(
            f"transition '{trigger}' produced an invalid task: "
            + "; ".join(item.message for item in diagnostics)
        )
    return updated
