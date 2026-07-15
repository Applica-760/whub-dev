"""Task record loading and built-in Workflow resolution."""
from __future__ import annotations

from importlib.resources import as_file, files
import os
from pathlib import Path
import tempfile
from typing import Any

import yaml
from pydantic import ValidationError

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import Diagnostic, WflowError
from whub.wflow.services.workflow import load_workflow


def load_task(path: Path) -> TaskDocument:
    """Load one task execution record from YAML."""
    try:
        return TaskDocument.model_validate(yaml.safe_load(path.read_text()))
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise WflowError(f"failed to load task YAML: {path}: {error}") from error


def load_task_workflow() -> WorkflowDefinition:
    """Load the built-in Workflow definition for task records."""
    resource = files("whub.wflow.definitions").joinpath("task.yaml")
    with as_file(resource) as path:
        return load_workflow(path)


def _values_at(data: Any, field: str, input_data: dict[str, Any]) -> list[Any]:
    if field.startswith("$input."):
        current: list[Any] = [input_data]
        parts = field.removeprefix("$input.").split(".")
    else:
        current = [data]
        parts = field.removeprefix("$").split(".")

    for part in parts:
        next_values: list[Any] = []
        for value in current:
            if part == "*" and isinstance(value, list):
                next_values.extend(value)
            elif isinstance(value, dict) and part in value:
                next_values.append(value[part])
        current = next_values
    return current


def _resolve_value(value: Any, data: dict[str, Any], input_data: dict[str, Any], actor: str) -> Any:
    if value == "$actor":
        return actor
    if isinstance(value, str) and value.startswith("$"):
        values = _values_at(data, value, input_data)
        if len(values) != 1:
            raise WflowError(f"record value '{value}' does not resolve to one value")
        return values[0]
    if isinstance(value, list):
        return [_resolve_value(item, data, input_data, actor) for item in value]
    if isinstance(value, dict):
        return {
            key: _resolve_value(item, data, input_data, actor)
            for key, item in value.items()
        }
    return value


def _requirement_error(
    requirement: Any,
    data: dict[str, Any],
    input_data: dict[str, Any],
) -> str | None:
    values = _values_at(data, requirement.field, input_data)
    if requirement.operator == "exists":
        if any(value is not None for value in values):
            return None
    elif requirement.operator == "all_in":
        if values and all(value in requirement.value for value in values):
            return None
    else:
        criteria = [
            criterion
            for value in values
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


def _transition_for(task: TaskDocument, workflow: WorkflowDefinition, trigger: str) -> Any:
    candidates = [
        transition
        for transition in workflow.transitions
        if transition.trigger == trigger and task.task.state in transition.source_states
    ]
    if not candidates:
        raise WflowError(
            f"trigger '{trigger}' is not allowed from state '{task.task.state}'"
        )
    return candidates[0]


def available_transitions(
    task: TaskDocument,
    workflow: WorkflowDefinition,
    input_data: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Return triggers whose requirements are currently satisfied."""
    data = task.model_dump(mode="python")
    inputs = input_data or {}
    return tuple(
        transition.trigger
        for transition in workflow.transitions
        if task.task.state in transition.source_states
        and not any(
            _requirement_error(requirement, data, inputs)
            for requirement in transition.requires
        )
    )


def apply_transition(
    task: TaskDocument,
    workflow: WorkflowDefinition,
    trigger: str,
    actor: str,
    input_data: dict[str, Any] | None = None,
) -> TaskDocument:
    """Apply one declared Workflow transition after validating its requirements."""
    diagnostics = check_task(task, workflow)
    if diagnostics:
        raise WflowError("task is invalid: " + "; ".join(item.message for item in diagnostics))

    transition = _transition_for(task, workflow, trigger)
    if actor != transition.actor:
        raise WflowError(f"trigger '{trigger}' requires actor '{transition.actor}'")

    data = task.model_dump(mode="python")
    inputs = input_data or {}
    errors = [
        error
        for requirement in transition.requires
        if (error := _requirement_error(requirement, data, inputs)) is not None
    ]
    if errors:
        raise WflowError("; ".join(errors))

    for record in transition.records:
        value = _resolve_value(record.value, data, inputs, actor)
        current = data.get(record.field)
        if isinstance(current, list):
            current.append(value)
        else:
            data[record.field] = value
    data["task"]["state"] = transition.to

    try:
        updated = TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"transition '{trigger}' produced an invalid task: {error}") from error
    diagnostics = check_task(updated, workflow)
    if diagnostics:
        raise WflowError(
            f"transition '{trigger}' produced an invalid task: "
            + "; ".join(item.message for item in diagnostics)
        )
    return updated


def update_step(
    task: TaskDocument,
    workflow: WorkflowDefinition,
    step_id: str,
    state: str,
    reason: str | None = None,
    log_summary: str | None = None,
    log_evidence: tuple[str, ...] = (),
) -> TaskDocument:
    """Mark the next incomplete Step done or skipped, logging a completed Phase."""
    if task.task.state != "in_progress":
        raise WflowError("steps can only be updated while the task is in_progress")
    diagnostics = check_task(task, workflow)
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
    steps = [step for phase in phases for step in phase["steps"]]
    next_step = next(
        (step for step in steps if step["state"] not in {"done", "skipped"}), None
    )
    if next_step is None:
        raise WflowError("all steps are already complete")
    if next_step["id"] != step_id:
        raise WflowError(f"next step is '{next_step['id']}', not '{step_id}'")

    next_step["state"] = state
    next_step["skip_reason"] = reason if state == "skipped" else None
    phase = next(phase for phase in phases if next_step in phase["steps"])
    if all(step["state"] in {"done", "skipped"} for step in phase["steps"]):
        if not log_summary:
            raise WflowError(f"completed phase '{phase['id']}' requires a log summary")
        data["logs"].append(
            {
                "phase": phase["id"],
                "summary": log_summary,
                "evidence": list(log_evidence),
            }
        )
    elif log_summary:
        raise WflowError("a log summary is only allowed when completing a phase")
    try:
        updated = TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to update step '{step_id}': {error}") from error
    return updated


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


def check_task(
    task: TaskDocument,
    workflow: WorkflowDefinition,
) -> tuple[Diagnostic, ...]:
    """Return semantic errors in TASK against WORKFLOW."""
    diagnostics: list[Diagnostic] = []

    # ケース1: Taskは対象Workflowと同じIDを持つ。
    if task.task.workflow != workflow.workflow.id:
        diagnostics.append(
            Diagnostic(
                "workflow_mismatch",
                f"task references '{task.task.workflow}', not '{workflow.workflow.id}'",
            )
        )

    # ケース2: Taskの状態はWorkflow定義の状態に含まれる。
    if task.task.state not in workflow.states:
        diagnostics.append(
            Diagnostic(
                "unknown_task_state",
                f"task state '{task.task.state}' is not defined by the Workflow",
            )
        )

    plan = task.plan
    requires_approval = task.task.state in {"in_progress", "completed"}
    approved_revisions = {approval.plan_revision for approval in task.approvals}

    # ケース3: 実行・完了には現在plan revisionの承認がある。
    if requires_approval and (plan is None or plan.revision not in approved_revisions):
        diagnostics.append(
            Diagnostic(
                "missing_plan_approval",
                "current plan revision is not approved",
            )
        )

    if plan is not None:
        steps = [step for phase in plan.phases for step in phase.steps]
        complete_states = {"done", "skipped"}
        first_incomplete = next(
            (index for index, step in enumerate(steps) if step.state not in complete_states),
            None,
        )

        # ケース4: 完了またはskipされたStepは先行Stepの後に置く。
        if first_incomplete is not None:
            for step in steps[first_incomplete + 1:]:
                if step.state in complete_states:
                    diagnostics.append(
                        Diagnostic(
                            "step_order_violation",
                            f"step '{step.id}' is complete before an earlier step",
                        )
                    )

        # ケース5: 完了Taskは全Step・受け入れ条件・結果を持つ。
        if task.task.state == "completed":
            if any(step.state not in complete_states for step in steps):
                diagnostics.append(
                    Diagnostic("incomplete_steps", "completed task has incomplete steps")
                )
            criteria = [
                *plan.acceptance,
                *(criterion for phase in plan.phases for criterion in phase.acceptance),
            ]
            passed = {
                result.acceptance
                for result in task.acceptance_results
                if result.status == "passed"
            }
            missing = [criterion.id for criterion in criteria if criterion.id not in passed]
            if missing:
                diagnostics.append(
                    Diagnostic(
                        "unsatisfied_acceptance",
                        f"completed task has unsatisfied acceptance: {', '.join(missing)}",
                    )
                )
            if task.result is None:
                diagnostics.append(
                    Diagnostic("missing_result", "completed task has no result")
                )

    # ケース6: 中止Taskは中止理由と実行者を記録する。
    if task.task.state == "cancelled" and task.cancellation is None:
        diagnostics.append(
            Diagnostic("missing_cancellation", "cancelled task has no cancellation"))

    return tuple(diagnostics)
