"""Current-state eligibility checks for Task operations."""

from __future__ import annotations

from collections.abc import Mapping

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import WorkflowDefinition
from whub.wflow.services.errors import Diagnostic
from whub.wflow.services.task.integrity import validate_task_set


def in_progress_error(task: TaskDocument, operation: str) -> str | None:
    """Return why OPERATION cannot run on TASK, if applicable."""
    if task.task.state == "paused":
        return f"{operation} cannot be performed while the task is paused"
    if task.task.state != "in_progress":
        return f"{operation} can only be performed while the task is in_progress"
    return None


def dependency_start_diagnostics(
    task: TaskDocument,
    tasks: Mapping[str, TaskDocument],
) -> tuple[Diagnostic, ...]:
    """Return unmet dependencies that prevent TASK from starting."""
    diagnostics: list[Diagnostic] = []
    for dependency in task.task.depends_on:
        target = tasks.get(dependency)
        if target is None:
            diagnostics.append(
                Diagnostic("missing_dependency", f"missing dependency: {dependency}")
            )
        elif target.task.state != "completed":
            diagnostics.append(
                Diagnostic(
                    "incomplete_dependency",
                    f"incomplete dependency: {dependency} ({target.task.state})",
                )
            )
    return tuple(diagnostics)


def interruption_start_diagnostics(
    parent: TaskDocument,
    child: TaskDocument,
    tasks: Mapping[str, TaskDocument],
    workflow: WorkflowDefinition,
    reason: str,
) -> tuple[tuple[str, Diagnostic], ...]:
    """Return why PARENT cannot start CHILD as an interruption."""
    diagnostics = list(validate_task_set(tasks, workflow))
    if parent.task.id == child.task.id:
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "same_interruption_task",
                    "interruption parent and child must differ",
                ),
            )
        )
    if parent.task.state != "in_progress":
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "interruption_parent_not_active",
                    "interruption parent must be in_progress",
                ),
            )
        )
    if child.task.state != "draft":
        diagnostics.append(
            (
                child.task.id,
                Diagnostic(
                    "interruption_child_not_draft", "interruption child must be draft"
                ),
            )
        )
    if child.plan is None:
        diagnostics.append(
            (
                child.task.id,
                Diagnostic("missing_plan", "interruption child has no plan"),
            )
        )
    if child.task.interruption_source_task_id is not None:
        diagnostics.append(
            (
                child.task.id,
                Diagnostic(
                    "interruption_child_has_source",
                    "interruption child already has a source",
                ),
            )
        )
    if not reason:
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "missing_interruption_reason", "interruption reason is required"
                ),
            )
        )
    if parent.task.interruption_task_id is not None:
        previous = tasks.get(parent.task.interruption_task_id)
        if previous is not None and previous.task.state in {"in_progress", "paused"}:
            diagnostics.append(
                (
                    parent.task.id,
                    Diagnostic(
                        "active_interruption_exists",
                        "interruption parent already has an active child",
                    ),
                )
            )
    diagnostics.extend(
        (child.task.id, diagnostic)
        for diagnostic in dependency_start_diagnostics(child, tasks)
    )
    return tuple(diagnostics)


def interruption_resume_diagnostics(
    parent: TaskDocument,
    tasks: Mapping[str, TaskDocument],
    workflow: WorkflowDefinition,
) -> tuple[tuple[str, Diagnostic], ...]:
    """Return why PARENT cannot resume from an interruption."""
    diagnostics = list(validate_task_set(tasks, workflow))
    if parent.task.state != "paused":
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "interruption_parent_not_paused",
                    "interruption parent must be paused",
                ),
            )
        )
    child_id = parent.task.interruption_task_id
    if child_id is None:
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "missing_interruption", "paused task has no interruption task"
                ),
            )
        )
        return tuple(diagnostics)
    child = tasks.get(child_id)
    if child is None:
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "missing_interruption_task",
                    f"interruption task not found: {child_id}",
                ),
            )
        )
        return tuple(diagnostics)
    if child.task.interruption_source_task_id != parent.task.id:
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "interruption_link_mismatch",
                    f"interruption task {child_id} does not reference parent {parent.task.id}",
                ),
            )
        )
    if child.task.state not in {"completed", "cancelled"}:
        diagnostics.append(
            (
                parent.task.id,
                Diagnostic(
                    "interruption_task_not_terminal",
                    f"interruption task {child_id} is not terminal: {child.task.state}",
                ),
            )
        )
    return tuple(diagnostics)
