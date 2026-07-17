"""Task Workflow state transitions."""
from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import TransitionRequirement, WorkflowDefinition
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task.integrity import validate_task
from whub.wflow.services.workflow import (
    apply_transition as apply_workflow_transition,
    available_transitions as available_workflow_transitions,
    values_at,
)


def _satisfied_if_defined(requirement: TransitionRequirement, data: dict[str, Any], input_data: dict[str, Any]) -> str | None:
    criteria = [criterion for value in values_at(data, requirement.field, input_data) for criterion in (value if isinstance(value, list) else [value]) if isinstance(criterion, dict)]
    if not criteria:
        return None
    passed = {result["acceptance"] for result in data.get(requirement.result_field, []) if result.get("status") == "passed"}
    return None if all(criterion["id"] in passed for criterion in criteria) else f"requirement not satisfied: {requirement.field} ({requirement.operator})"


_TASK_REQUIREMENT_EVALUATORS = {"satisfied_if_defined": _satisfied_if_defined}


def available_transitions(task: TaskDocument, workflow: WorkflowDefinition, input_data: dict[str, Any] | None = None) -> tuple[str, ...]:
    return available_workflow_transitions(workflow, task.task.state, task.model_dump(mode="python"), input_data, _TASK_REQUIREMENT_EVALUATORS)


def apply_transition(task: TaskDocument, workflow: WorkflowDefinition, trigger: str, actor: str, input_data: dict[str, Any] | None = None) -> TaskDocument:
    diagnostics = validate_task(task, workflow)
    if diagnostics:
        raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))
    data = task.model_dump(mode="python")
    state, data = apply_workflow_transition(workflow, task.task.state, data, trigger, actor, input_data, _TASK_REQUIREMENT_EVALUATORS)
    data["task"]["state"] = state
    try:
        updated = TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"transition '{trigger}' produced an invalid task: {error}") from error
    diagnostics = validate_task(updated, workflow)
    if diagnostics:
        raise WflowError(f"transition '{trigger}' produced an invalid task: " + "; ".join(item.message for item in diagnostics))
    return updated
