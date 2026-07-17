"""Task content operations."""
from __future__ import annotations

import re

from pydantic import ValidationError

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import WflowError
from whub.wflow.services.task.eligibility import in_progress_error
from whub.wflow.services.task.integrity import validate_task


STEP_REFERENCE_PATTERN = r"^[0-9]{3}-[0-9]{3}$"
PHASE_REFERENCE_PATTERN = r"^[0-9]{3}$"


def update_step(task: TaskDocument, workflow: WorkflowDefinition, step_ref: str | None, state: str, reason: str | None = None, logs: tuple[str, ...] = ()) -> TaskDocument:
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
    if step_ref is None:
        selected = next(((phase_index, step_index) for phase_index, phase in enumerate(phases) for step_index, step in enumerate(phase["steps"]) if step["state"] not in {"done", "skipped"}), None)
        if selected is None:
            raise WflowError("all steps are already complete")
        phase_index, step_index = selected
    else:
        if re.fullmatch(STEP_REFERENCE_PATTERN, step_ref) is None:
            raise WflowError("step reference must be PPP-SSS, for example '002-003'")
        phase_index, step_index = (int(part) - 1 for part in step_ref.split("-"))
        if phase_index < 0 or phase_index >= len(phases) or step_index < 0 or step_index >= len(phases[phase_index]["steps"]):
            raise WflowError(f"step reference not found: {step_ref}")
    phase = phases[phase_index]
    step = phase["steps"][step_index]
    if step["state"] in {"done", "skipped"}:
        raise WflowError(f"step is already complete: {phase_index + 1:03}-{step_index + 1:03}")
    step["state"] = state
    step["skip_reason"] = reason if state == "skipped" else None
    if all(item["state"] in {"done", "skipped"} for item in phase["steps"]) and not logs:
        raise WflowError(f"completed phase {phase_index + 1:03} requires a log")
    phase["log"].extend(logs)
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to update step '{step_ref or 'next'}': {error}") from error


def append_phase_log(task: TaskDocument, phase_ref: str, logs: tuple[str, ...]) -> TaskDocument:
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


def record_acceptance(task: TaskDocument, acceptance: str, status: str, evidence: tuple[str, ...] = ()) -> TaskDocument:
    """Record one acceptance result while a Task is in progress."""
    if error := in_progress_error(task, "acceptance"):
        raise WflowError(error)
    if task.plan is None:
        raise WflowError("task has no plan")
    if status not in {"passed", "failed"}:
        raise WflowError(f"unsupported acceptance status '{status}'")
    criteria = [*task.plan.acceptance, *(criterion for phase in task.plan.phases for criterion in phase.acceptance)]
    if acceptance not in {criterion.id for criterion in criteria}:
        raise WflowError(f"unknown acceptance '{acceptance}'")
    if any(result.acceptance == acceptance for result in task.acceptance_results):
        raise WflowError(f"acceptance '{acceptance}' is already recorded")
    data = task.model_dump(mode="python")
    data["acceptance_results"].append({"acceptance": acceptance, "status": status, "evidence": list(evidence)})
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to record acceptance '{acceptance}': {error}") from error
