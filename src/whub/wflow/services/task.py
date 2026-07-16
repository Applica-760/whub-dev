"""Task record loading and built-in Workflow resolution."""
from __future__ import annotations

from importlib.resources import as_file, files
import os
from pathlib import Path
import re
import tempfile
from typing import Any

import yaml
from pydantic import ValidationError

from whub.wflow.models.task import TASK_ID_PATTERN, TaskDocument, TaskSummary
from whub.wflow.models.workflow import TransitionRequirement, WorkflowDefinition
from whub.wflow.services.errors import Diagnostic, WflowError
from whub.wflow.services.workflow import (
    apply_transition as apply_workflow_transition,
    available_transitions as available_workflow_transitions,
    load_workflow,
    values_at,
)

STEP_REFERENCE_PATTERN = r"^[0-9]{3}-[0-9]{3}$"


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
            f"{item.code}: {item.message}" for item in check_task(record, workflow)
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
    diagnostics = check_task(task, workflow)
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
    step_ref: str | None,
    state: str,
    reason: str | None = None,
    log_summary: str | None = None,
    log_evidence: tuple[str, ...] = (),
) -> TaskDocument:
    """Update a selected or next incomplete Step, logging a completed Phase."""
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
    if all(step["state"] in {"done", "skipped"} for step in phase["steps"]):
        if not log_summary:
            raise WflowError(f"completed phase {phase_index + 1:03} requires a log summary")
        phase["log"] = {
            "summary": log_summary,
            "evidence": list(log_evidence),
        }
    elif log_summary:
        raise WflowError("a log summary is only allowed when completing a phase")
    try:
        updated = TaskDocument.model_validate(data)
    except ValidationError as error:
        raise WflowError(f"failed to update step '{step_id}': {error}") from error
    return updated


def record_acceptance(
    task: TaskDocument,
    acceptance: str,
    status: str,
    evidence: tuple[str, ...] = (),
) -> TaskDocument:
    """Record one acceptance result while a Task is in progress."""
    if task.task.state != "in_progress":
        raise WflowError("acceptance can only be recorded while the task is in_progress")
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


def check_task(
    task: TaskDocument,
    workflow: WorkflowDefinition,
) -> tuple[Diagnostic, ...]:
    """Return semantic errors in TASK against WORKFLOW."""
    diagnostics: list[Diagnostic] = []

    # ケース1: Taskの状態はWorkflow定義の状態に含まれる。
    if task.task.state not in workflow.states:
        diagnostics.append(
            Diagnostic(
                "unknown_task_state",
                f"task state '{task.task.state}' is not defined by the Workflow",
            )
        )

    plan = task.plan
    requires_approval = task.task.state in {"in_progress", "completed"}

    # ケース2: 実行・完了にはplan承認がある。
    if requires_approval and (plan is None or not task.approvals):
        diagnostics.append(
            Diagnostic(
                "missing_plan_approval",
                "plan is not approved",
            )
        )

    if plan is not None:
        steps = [step for phase in plan.phases for step in phase.steps]
        complete_states = {"done", "skipped"}

        # ケース3: 完了Taskは全Step・受け入れ条件・結果を持つ。
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

    # ケース4: 中止Taskは中止理由と実行者を記録する。
    if task.task.state == "cancelled" and task.cancellation is None:
        diagnostics.append(
            Diagnostic("missing_cancellation", "cancelled task has no cancellation"))

    return tuple(diagnostics)
