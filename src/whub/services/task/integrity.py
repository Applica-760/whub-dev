"""Task runtime semantic validation."""

from __future__ import annotations

from collections.abc import Mapping

from whub.models.flow import TaskRuntime, WorkflowDefinition
from whub.services.flow.errors import Diagnostic


def validate_task(
    task: TaskRuntime, workflow: WorkflowDefinition
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    if task.workflow != workflow.workflow.id:
        diagnostics.append(
            Diagnostic("workflow_mismatch", "task workflow is not loaded workflow")
        )
    if task.state not in workflow.states:
        diagnostics.append(
            Diagnostic(
                "unknown_task_state",
                f"task state '{task.state}' is not defined by the Workflow",
            )
        )
    if task.state == "paused" and task.interruption_task_id is None:
        diagnostics.append(
            Diagnostic("missing_interruption", "paused task has no interruption task")
        )
    return tuple(diagnostics)


def validate_task_interruption(
    task: TaskRuntime, tasks: Mapping[str, TaskRuntime]
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    active_states = {"in_progress", "paused"}

    if child_id := task.interruption_task_id:
        child = tasks.get(child_id)
        if child is None:
            diagnostics.append(
                Diagnostic(
                    "missing_interruption_task",
                    f"interruption task not found: {child_id}",
                )
            )
        elif child.interruption_source_task_id != task.id:
            diagnostics.append(
                Diagnostic(
                    "interruption_link_mismatch",
                    f"interruption task {child.id} does not reference source {task.id}",
                )
            )
        elif child.state in active_states and task.state not in {"paused", "cancelled"}:
            diagnostics.append(
                Diagnostic(
                    "active_interruption_source_not_paused",
                    f"task {task.id} must be paused while interruption task {child.id} is active",
                )
            )

    if source_id := task.interruption_source_task_id:
        source = tasks.get(source_id)
        if source is None:
            diagnostics.append(
                Diagnostic(
                    "missing_interruption_source",
                    f"interruption source not found: {source_id}",
                )
            )
        elif task.state in active_states:
            if source.interruption_task_id != task.id:
                diagnostics.append(
                    Diagnostic(
                        "interruption_link_mismatch",
                        f"interruption source {source.id} does not reference task {task.id}",
                    )
                )
            elif source.state not in {"paused", "cancelled"}:
                diagnostics.append(
                    Diagnostic(
                        "active_interruption_source_not_paused",
                        f"interruption source {source.id} is not paused or cancelled",
                    )
                )

    active_children = [
        candidate
        for candidate in tasks.values()
        if candidate.interruption_source_task_id == task.id
        and candidate.state in active_states
    ]
    if len(active_children) > 1:
        diagnostics.append(
            Diagnostic(
                "multiple_active_interruptions",
                f"task {task.id} has multiple active interruption tasks",
            )
        )
    return tuple(diagnostics)


def validate_task_set(
    tasks: Mapping[str, TaskRuntime], workflow: WorkflowDefinition
) -> tuple[tuple[str, Diagnostic], ...]:
    return tuple(
        (task_id, diagnostic)
        for task_id, task in tasks.items()
        if not task.legacy
        for diagnostic in (
            *validate_task(task, workflow),
            *validate_task_interruption(task, tasks),
        )
    )
