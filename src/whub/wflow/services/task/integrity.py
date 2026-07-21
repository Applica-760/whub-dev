"""Task execution record semantic validation."""

from __future__ import annotations

from collections.abc import Mapping

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
    requires_approval = task.task.state in {"in_progress", "paused", "completed"}

    # ケース2: 実行・完了にはplan承認がある。
    if requires_approval and (plan is None or not task.approvals):
        diagnostics.append(
            Diagnostic(
                "missing_plan_approval",
                "plan is not approved",
            )
        )

    if task.task.state == "paused" and task.task.interruption_task_id is None:
        diagnostics.append(
            Diagnostic(
                "missing_interruption",
                "paused task has no interruption task",
            )
        )

    if plan is not None:
        steps = [
            step
            for phase in plan.phases
            if not phase.deleted
            for step in phase.steps
            if not step.deleted
        ]
        complete_states = {"done", "skipped"}

        # ケース3: 完了Taskは全Step・受け入れ条件・結果を持つ。
        if task.task.state == "completed":
            if any(step.state not in complete_states for step in steps):
                diagnostics.append(
                    Diagnostic(
                        "incomplete_steps", "completed task has incomplete steps"
                    )
                )
            criteria = [
                *plan.acceptance,
                *(
                    criterion
                    for phase in plan.phases
                    if not phase.deleted
                    for criterion in phase.acceptance
                ),
            ]
            passed = {
                result.acceptance
                for result in task.acceptance_results
                if result.status == "passed"
            }
            missing = [
                criterion.id for criterion in criteria if criterion.id not in passed
            ]
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


def validate_task_interruption(
    task: TaskDocument,
    tasks: Mapping[str, TaskDocument],
) -> tuple[Diagnostic, ...]:
    """Return cross-Task interruption relationship errors for TASK."""
    diagnostics: list[Diagnostic] = []
    active_states = {"in_progress", "paused"}
    header = task.task

    if header.interruption_task_id is not None:
        child = tasks.get(header.interruption_task_id)
        if child is None:
            diagnostics.append(
                Diagnostic(
                    "missing_interruption_task",
                    f"interruption task not found: {header.interruption_task_id}",
                )
            )
        elif child.task.interruption_source_task_id != header.id:
            diagnostics.append(
                Diagnostic(
                    "interruption_link_mismatch",
                    f"interruption task {child.task.id} does not reference source {header.id}",
                )
            )
        elif child.task.state in active_states and header.state not in {
            "paused",
            "cancelled",
        }:
            diagnostics.append(
                Diagnostic(
                    "active_interruption_source_not_paused",
                    f"task {header.id} must be paused while interruption task {child.task.id} is active",
                )
            )

    if header.interruption_source_task_id is not None:
        source = tasks.get(header.interruption_source_task_id)
        if source is None:
            diagnostics.append(
                Diagnostic(
                    "missing_interruption_source",
                    f"interruption source not found: {header.interruption_source_task_id}",
                )
            )
        elif header.state in active_states:
            if source.task.interruption_task_id != header.id:
                diagnostics.append(
                    Diagnostic(
                        "interruption_link_mismatch",
                        f"interruption source {source.task.id} does not reference task {header.id}",
                    )
                )
            elif source.task.state not in {"paused", "cancelled"}:
                diagnostics.append(
                    Diagnostic(
                        "active_interruption_source_not_paused",
                        f"interruption source {source.task.id} is not paused or cancelled",
                    )
                )

    active_children = [
        candidate
        for candidate in tasks.values()
        if candidate.task.interruption_source_task_id == header.id
        and candidate.task.state in active_states
    ]
    if len(active_children) > 1:
        diagnostics.append(
            Diagnostic(
                "multiple_active_interruptions",
                f"task {header.id} has multiple active interruption tasks",
            )
        )

    return tuple(diagnostics)


def validate_task_set(
    tasks: Mapping[str, TaskDocument],
    workflow: WorkflowDefinition,
) -> tuple[tuple[str, Diagnostic], ...]:
    """Return structural and interruption diagnostics for a Task set."""
    return tuple(
        (task_id, diagnostic)
        for task_id, task in tasks.items()
        for diagnostic in (
            *validate_task(task, workflow),
            *validate_task_interruption(task, tasks),
        )
    )
