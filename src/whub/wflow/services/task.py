"""Task record loading and built-in Workflow resolution."""
from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

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
