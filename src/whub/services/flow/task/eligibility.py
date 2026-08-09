"""Eligibility checks for Task runtime relations."""

from __future__ import annotations

from collections.abc import Mapping

from whub.models.flow import TaskRuntime, WorkflowDefinition
from whub.services.flow.errors import Diagnostic
from whub.services.flow.task.integrity import validate_task_set


def dependency_start_diagnostics(
    task: TaskRuntime, tasks: Mapping[str, TaskRuntime]
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    for dependency in task.depends_on:
        target = tasks.get(dependency)
        if target is None:
            diagnostics.append(
                Diagnostic("missing_dependency", f"missing dependency: {dependency}")
            )
        elif target.state != "completed":
            diagnostics.append(
                Diagnostic(
                    "incomplete_dependency",
                    f"incomplete dependency: {dependency} ({target.state})",
                )
            )
    return tuple(diagnostics)


def interruption_start_diagnostics(
    parent: TaskRuntime,
    child: TaskRuntime,
    tasks: Mapping[str, TaskRuntime],
    workflow: WorkflowDefinition,
    reason: str,
) -> tuple[tuple[str, Diagnostic], ...]:
    diagnostics = list(validate_task_set(tasks, workflow))
    if parent.id == child.id:
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "same_interruption_task",
                    "interruption parent and child must differ",
                ),
            )
        )
    if parent.state != "in_progress":
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "interruption_parent_not_active",
                    "interruption parent must be in_progress",
                ),
            )
        )
    if child.state not in {"draft", "in_progress"}:
        diagnostics.append(
            (
                child.id,
                Diagnostic(
                    "interruption_child_not_startable",
                    "interruption child must be draft or in_progress",
                ),
            )
        )
    if child.interruption_source_task_id is not None:
        diagnostics.append(
            (
                child.id,
                Diagnostic(
                    "interruption_child_has_source",
                    "interruption child already has a source",
                ),
            )
        )
    if not reason:
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "missing_interruption_reason", "interruption reason is required"
                ),
            )
        )
    if parent.interruption_task_id:
        previous = tasks.get(parent.interruption_task_id)
        if previous is not None and previous.state in {"in_progress", "paused"}:
            diagnostics.append(
                (
                    parent.id,
                    Diagnostic(
                        "active_interruption_exists",
                        "interruption parent already has an active child",
                    ),
                )
            )
    diagnostics.extend(
        (child.id, diagnostic)
        for diagnostic in dependency_start_diagnostics(child, tasks)
    )
    return tuple(diagnostics)


def interruption_resume_diagnostics(
    parent: TaskRuntime,
    tasks: Mapping[str, TaskRuntime],
    workflow: WorkflowDefinition,
) -> tuple[tuple[str, Diagnostic], ...]:
    diagnostics = list(validate_task_set(tasks, workflow))
    if parent.state != "paused":
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "interruption_parent_not_paused",
                    "interruption parent must be paused",
                ),
            )
        )
    if parent.interruption_task_id is None:
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "missing_interruption", "paused task has no interruption task"
                ),
            )
        )
        return tuple(diagnostics)
    child = tasks.get(parent.interruption_task_id)
    if child is None:
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "missing_interruption_task",
                    f"interruption task not found: {parent.interruption_task_id}",
                ),
            )
        )
    elif child.interruption_source_task_id != parent.id:
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "interruption_link_mismatch",
                    f"interruption task {child.id} does not reference parent {parent.id}",
                ),
            )
        )
    elif child.state not in {"completed", "cancelled"}:
        diagnostics.append(
            (
                parent.id,
                Diagnostic(
                    "interruption_task_not_terminal",
                    f"interruption task {child.id} is not terminal: {child.state}",
                ),
            )
        )
    return tuple(diagnostics)
