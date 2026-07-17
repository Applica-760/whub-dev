"""Task execution record mutations."""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile
from typing import Any

import yaml
from pydantic import ValidationError

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import TransitionRequirement, WorkflowDefinition
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task_eligibility import in_progress_error
from whub.wflow.services.task_integrity import validate_task
from whub.wflow.services.workflow import (
    apply_transition as apply_workflow_transition,
    available_transitions as available_workflow_transitions,
    values_at,
)


STEP_REFERENCE_PATTERN = r"^[0-9]{3}-[0-9]{3}$"
PHASE_REFERENCE_PATTERN = r"^[0-9]{3}$"


def _satisfied_if_defined(
    requirement: TransitionRequirement,
    data: dict[str, Any],
    input_data: dict[str, Any],
) -> str | None:
    criteria = [
        criterion
        for value in values_at(data, requirement.field, input_data)
        for criterion in (value if isinstance(value, list) else [value])
        if isinstance(criterion, dict)
    ]
    if not criteria:
        return None
    results = data.get(requirement.result_field, [])
    passed = {
        result["acceptance"]
        for result in results
        if result.get("status") == "passed"
    }
    if all(criterion["id"] in passed for criterion in criteria):
        return None
    return f"requirement not satisfied: {requirement.field} ({requirement.operator})"


_TASK_REQUIREMENT_EVALUATORS = {"satisfied_if_defined": _satisfied_if_defined}


def available_transitions(
    task: TaskDocument,
    workflow: WorkflowDefinition,
    input_data: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return triggers whose requirements are currently satisfied."""
    return available_workflow_transitions(
        workflow,
        task.task.state,
        task.model_dump(mode="python"),
        input_data,
        _TASK_REQUIREMENT_EVALUATORS,
    )


def apply_transition(
    task: TaskDocument,
    workflow: WorkflowDefinition,
    trigger: str,
    actor: str,
    input_data: dict[str, Any] | None = None,
) -> TaskDocument:
    """Apply one declared Workflow transition after validating its requirements."""
    diagnostics = validate_task(task, workflow)
    if diagnostics:
        raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))

    data = task.model_dump(mode="python")
    state, data = apply_workflow_transition(
        workflow,
        task.task.state,
        data,
        trigger,
        actor,
        input_data,
        _TASK_REQUIREMENT_EVALUATORS,
    )
    data["task"]["state"] = state

    try:
        updated = TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"transition '{trigger}' produced an invalid task: {error}") from error
    diagnostics = validate_task(updated, workflow)
    if diagnostics:
        raise WflowError(
            f"transition '{trigger}' produced an invalid task: "
            + "; ".join(item.message for item in diagnostics)
        )
    return updated


def update_step(
    task: TaskDocument,
    workflow: WorkflowDefinition,
    step_ref: str | None,
    state: str,
    reason: str | None = None,
    logs: tuple[str, ...] = (),
) -> TaskDocument:
    """Update a selected or next incomplete Step, logging a completed Phase."""
    if error := in_progress_error(task, "steps"):
        raise WflowError(error)
    diagnostics = validate_task(task, workflow)
    if diagnostics:
        raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))
    if task.plan is None:
        raise WflowError("task has no plan")
    if state not in {"done", "skipped"}:
        raise WflowError(f"unsupported step state '{state}'")
    if state == "skipped" and not reason:
        raise WflowError("skipped step requires a reason")

    data = task.model_dump(mode="python")
    phases = data["plan"]["phases"]
    phase_index: int
    step_index: int
    if step_ref is None:
        selected = next(
            (
                (current_phase_index, current_step_index)
                for current_phase_index, phase in enumerate(phases)
                for current_step_index, step in enumerate(phase["steps"])
                if step["state"] not in {"done", "skipped"}
            ),
            None,
        )
        if selected is None:
            raise WflowError("all steps are already complete")
        phase_index, step_index = selected
    else:
        if re.fullmatch(STEP_REFERENCE_PATTERN, step_ref) is None:
            raise WflowError("step reference must be PPP-SSS, for example '002-003'")
        phase_index, step_index = (int(part) - 1 for part in step_ref.split("-"))
        if (
            phase_index < 0
            or phase_index >= len(phases)
            or step_index < 0
            or step_index >= len(phases[phase_index]["steps"])
        ):
            raise WflowError(f"step reference not found: {step_ref}")

    phase = phases[phase_index]
    step = phase["steps"][step_index]
    if step["state"] in {"done", "skipped"}:
        raise WflowError(f"step is already complete: {phase_index + 1:03}-{step_index + 1:03}")
    step["state"] = state
    step["skip_reason"] = reason if state == "skipped" else None
    phase_completed = all(step["state"] in {"done", "skipped"} for step in phase["steps"])
    if phase_completed and not logs:
        raise WflowError(f"completed phase {phase_index + 1:03} requires a log")
    phase["log"].extend(logs)
    try:
        updated = TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to update step '{step_id}': {error}") from error
    return updated


def append_phase_log(
    task: TaskDocument,
    phase_ref: str,
    logs: tuple[str, ...],
) -> TaskDocument:
    """Append log lines to one Phase without changing its Steps."""
    if task.task.state not in {"in_progress", "paused"}:
        raise WflowError("phase logs can only be recorded while the task is in_progress or paused")
    if task.plan is None:
        raise WflowError("task has no plan")
    if not logs:
        raise WflowError("at least one log is required")
    if re.fullmatch(PHASE_REFERENCE_PATTERN, phase_ref) is None:
        raise WflowError("phase reference must be PPP, for example '002'")

    phase_index = int(phase_ref) - 1
    if phase_index < 0 or phase_index >= len(task.plan.phases):
        raise WflowError(f"phase reference not found: {phase_ref}")

    data = task.model_dump(mode="python")
    data["plan"]["phases"][phase_index]["log"].extend(logs)
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to append phase log '{phase_ref}': {error}") from error


def record_acceptance(
    task: TaskDocument,
    acceptance: str,
    status: str,
    evidence: tuple[str, ...] = (),
) -> TaskDocument:
    """Record one acceptance result while a Task is in progress."""
    if error := in_progress_error(task, "acceptance"):
        raise WflowError(error)
    if task.plan is None:
        raise WflowError("task has no plan")
    if status not in {"passed", "failed"}:
        raise WflowError(f"unsupported acceptance status '{status}'")

    criteria = [
        *task.plan.acceptance,
        *(criterion for phase in task.plan.phases for criterion in phase.acceptance),
    ]
    if acceptance not in {criterion.id for criterion in criteria}:
        raise WflowError(f"unknown acceptance '{acceptance}'")
    if any(result.acceptance == acceptance for result in task.acceptance_results):
        raise WflowError(f"acceptance '{acceptance}' is already recorded")

    data = task.model_dump(mode="python")
    data["acceptance_results"].append(
        {
            "acceptance": acceptance,
            "status": status,
            "evidence": list(evidence),
        }
    )
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to record acceptance '{acceptance}': {error}") from error


def write_task(path: Path, task: TaskDocument) -> None:
    """Atomically write a validated Task record."""
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
                    task.model_dump(mode="json"),
                    allow_unicode=True,
                    sort_keys=False,
                )
            )
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    except OSError as error:
        raise WflowError(f"failed to write task YAML: {path}: {error}") from error
