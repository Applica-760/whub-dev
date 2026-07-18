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
        selected = next(((phase_index, step_index) for phase_index, phase in enumerate(phases) if not phase["deleted"] for step_index, step in enumerate(phase["steps"]) if not step["deleted"] and step["state"] not in {"done", "skipped"}), None)
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
    if phase["deleted"] or step["deleted"]:
        raise WflowError(f"step is deleted: {step_ref}")
    if step["state"] in {"done", "skipped"}:
        raise WflowError(f"step is already complete: {phase_index + 1:03}-{step_index + 1:03}")
    step["state"] = state
    step["skip_reason"] = reason if state == "skipped" else None
    if all(item["state"] in {"done", "skipped"} for item in phase["steps"] if not item["deleted"]) and not logs:
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


def delete_plan_item(task: TaskDocument, reference: str) -> TaskDocument:
    """Logically delete one pending Phase or Step while the Task is draft."""
    if task.task.state != "draft":
        raise WflowError("plan operations require a draft task")
    if task.plan is None:
        raise WflowError("task has no plan")
    data = task.model_dump(mode="python")
    phases = data["plan"]["phases"]
    if re.fullmatch(PHASE_REFERENCE_PATTERN, reference):
        phase_index = int(reference) - 1
        if phase_index < 0 or phase_index >= len(phases):
            raise WflowError(f"phase reference not found: {reference}")
        phase = phases[phase_index]
        if phase["deleted"]:
            raise WflowError(f"phase is deleted: {reference}")
        if phase["log"] or any(step["state"] in {"done", "skipped"} for step in phase["steps"]):
            raise WflowError(f"phase has execution history: {reference}")
        phase["deleted"] = True
    elif re.fullmatch(STEP_REFERENCE_PATTERN, reference):
        phase_index, step_index = (int(part) - 1 for part in reference.split("-"))
        if phase_index < 0 or phase_index >= len(phases) or step_index < 0 or step_index >= len(phases[phase_index]["steps"]):
            raise WflowError(f"step reference not found: {reference}")
        phase = phases[phase_index]
        step = phase["steps"][step_index]
        if phase["deleted"] or step["deleted"]:
            raise WflowError(f"step is deleted: {reference}")
        if step["state"] in {"done", "skipped"}:
            raise WflowError(f"step has execution history: {reference}")
        step["deleted"] = True
    else:
        raise WflowError("plan reference must be PPP or PPP-SSS")
    return TaskDocument.model_validate(data)


def insert_plan_step(
    task: TaskDocument,
    description: str,
    after: str | None = None,
    phase_title: str | None = None,
    phase_ref: str | None = None,
) -> TaskDocument:
    """Insert a named Phase or a pending Step into a draft Task plan."""
    if task.task.state != "draft":
        raise WflowError("plan operations require a draft task")
    if phase_title is not None and phase_ref is not None:
        raise WflowError("phase_title and phase_ref cannot be used together")
    data = task.model_dump(mode="python")
    step = {"description": description, "state": "pending", "skip_reason": None, "deleted": False}
    phase = {
        "title": phase_title or "挿入フェーズ",
        "acceptance": [],
        "steps": [step],
        "log": [],
        "deleted": False,
    }
    if data["plan"] is None:
        if phase_ref is not None:
            raise WflowError("task has no plan")
        data["plan"] = {"acceptance": [], "phases": [phase]}
    else:
        phases = data["plan"]["phases"]
        if phase_title is not None:
            if after is None:
                phases.append(phase)
            elif re.fullmatch(PHASE_REFERENCE_PATTERN, after):
                phase_index = int(after) - 1
                if phase_index < 0 or phase_index >= len(phases) or phases[phase_index]["deleted"]:
                    raise WflowError(f"phase reference not found: {after}")
                phases.insert(phase_index + 1, phase)
            else:
                raise WflowError("phase reference must be PPP, for example '002'")
        elif phase_ref is not None:
            if re.fullmatch(PHASE_REFERENCE_PATTERN, phase_ref) is None:
                raise WflowError("phase reference must be PPP, for example '002'")
            phase_index = int(phase_ref) - 1
            if phase_index < 0 or phase_index >= len(phases) or phases[phase_index]["deleted"]:
                raise WflowError(f"phase reference not found: {phase_ref}")
            steps = phases[phase_index]["steps"]
            if after is None:
                steps.append(step)
            elif re.fullmatch(STEP_REFERENCE_PATTERN, after):
                after_phase_index, step_index = (int(part) - 1 for part in after.split("-"))
                if after_phase_index != phase_index:
                    raise WflowError(f"step reference is not in phase {phase_ref}: {after}")
                if step_index < 0 or step_index >= len(steps) or steps[step_index]["deleted"]:
                    raise WflowError(f"step reference not found: {after}")
                steps.insert(step_index + 1, step)
            else:
                raise WflowError("step reference must be PPP-SSS, for example '002-003'")
        elif after is None:
            first = next((item for item in phases if not item["deleted"]), None)
            if first is None:
                phases.insert(0, phase)
            else:
                first["steps"].insert(0, step)
        elif re.fullmatch(PHASE_REFERENCE_PATTERN, after):
            phase_index = int(after) - 1
            if phase_index < 0 or phase_index >= len(phases) or phases[phase_index]["deleted"]:
                raise WflowError(f"phase reference not found: {after}")
            phases.insert(phase_index + 1, phase)
        elif re.fullmatch(STEP_REFERENCE_PATTERN, after):
            phase_index, step_index = (int(part) - 1 for part in after.split("-"))
            if phase_index < 0 or phase_index >= len(phases) or step_index < 0 or step_index >= len(phases[phase_index]["steps"]):
                raise WflowError(f"step reference not found: {after}")
            target_phase = phases[phase_index]
            if target_phase["deleted"] or target_phase["steps"][step_index]["deleted"]:
                raise WflowError(f"step is deleted: {after}")
            target_phase["steps"].insert(step_index + 1, step)
        else:
            raise WflowError("plan reference must be PPP or PPP-SSS")
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to insert plan item: {error}") from error


def update_plan_item(task: TaskDocument, reference: str, description: str) -> TaskDocument:
    """Update a pending Phase title or Step description in a draft Task."""
    if task.task.state != "draft":
        raise WflowError("plan operations require a draft task")
    if task.plan is None:
        raise WflowError("task has no plan")
    data = task.model_dump(mode="python")
    phases = data["plan"]["phases"]
    if re.fullmatch(PHASE_REFERENCE_PATTERN, reference):
        phase_index = int(reference) - 1
        if phase_index < 0 or phase_index >= len(phases) or phases[phase_index]["deleted"]:
            raise WflowError(f"phase reference not found: {reference}")
        phases[phase_index]["title"] = description
    elif re.fullmatch(STEP_REFERENCE_PATTERN, reference):
        phase_index, step_index = (int(part) - 1 for part in reference.split("-"))
        if phase_index < 0 or phase_index >= len(phases) or step_index < 0 or step_index >= len(phases[phase_index]["steps"]):
            raise WflowError(f"step reference not found: {reference}")
        phase = phases[phase_index]
        step = phase["steps"][step_index]
        if phase["deleted"] or step["deleted"]:
            raise WflowError(f"step is deleted: {reference}")
        if step["state"] in {"done", "skipped"}:
            raise WflowError(f"step has execution history: {reference}")
        step["description"] = description
    else:
        raise WflowError("plan reference must be PPP or PPP-SSS")
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to update plan item '{reference}': {error}") from error


def update_dependency(task: TaskDocument, dependency: str, add: bool) -> TaskDocument:
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
        raise WflowError(f"failed to update dependency '{dependency}': {error}") from error


def update_acceptance(
    task: TaskDocument,
    value: str,
    add: bool,
    phase_ref: str | None = None,
) -> TaskDocument:
    """Add or remove one Task or Phase acceptance criterion while draft."""
    if task.task.state != "draft":
        raise WflowError("acceptance operations require a draft task")
    if task.plan is None:
        raise WflowError("task has no plan")
    if not add and phase_ref is not None:
        raise WflowError("--phase is only allowed when adding acceptance")
    data = task.model_dump(mode="python")
    plan = data["plan"]
    if add:
        criteria = [
            *plan["acceptance"],
            *(criterion for phase in plan["phases"] for criterion in phase["acceptance"]),
        ]
        numbers = [int(item["id"].removeprefix("ACC-")) for item in criteria]
        criterion = {"id": f"ACC-{max(numbers, default=0) + 1:03}", "statement": value}
        if phase_ref is None:
            plan["acceptance"].append(criterion)
        elif re.fullmatch(PHASE_REFERENCE_PATTERN, phase_ref):
            phase_index = int(phase_ref) - 1
            if phase_index < 0 or phase_index >= len(plan["phases"]):
                raise WflowError(f"phase reference not found: {phase_ref}")
            phase = plan["phases"][phase_index]
            if phase["deleted"]:
                raise WflowError(f"phase is deleted: {phase_ref}")
            phase["acceptance"].append(criterion)
        else:
            raise WflowError("phase reference must be PPP, for example '002'")
    else:
        containers = [plan["acceptance"], *(phase["acceptance"] for phase in plan["phases"])]
        for criteria in containers:
            for index, criterion in enumerate(criteria):
                if criterion["id"] == value:
                    del criteria[index]
                    try:
                        return TaskDocument.model_validate(data)
                    except ValidationError as error:
                        raise WflowError(f"failed to remove acceptance '{value}': {error}") from error
        raise WflowError(f"acceptance not found: {value}")
    try:
        return TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to add acceptance: {error}") from error
