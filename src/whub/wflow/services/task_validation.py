"""Semantic validation for Task execution records."""
from __future__ import annotations

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import Diagnostic


def validate_task(
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
            Diagnostic("missing_cancellation", "cancelled task has no cancellation")
        )

    return tuple(diagnostics)
