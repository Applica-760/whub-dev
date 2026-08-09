"""Task Flow runtime contract tests."""

from __future__ import annotations

import pytest

from whub.models.flow import TaskRuntime
from whub.services.flow.definitions import task_workflow
from whub.services.flow.errors import FlowError
from whub.services.flow.task import (
    apply_transition,
    available_transitions,
    interrupt_task,
    load_task,
    load_task_markdown,
    resume_task,
    task_markdown_path,
    update_dependency,
    write_task,
    write_task_markdown,
)


def _task(task_id: str, state: str = "draft") -> TaskRuntime:
    return TaskRuntime(schema_version=2, id=task_id, workflow="WF-001", state=state)


def test_runtime_yaml_excludes_legacy_task_document(tmp_path) -> None:
    path = tmp_path / "task.yaml"
    task = _task("TASK-001")
    write_task(path, task)
    assert load_task(path) == task

    path.write_text("schema_version: 1\ntask:\n  id: TASK-001\n  state: draft\n")
    with pytest.raises(FlowError, match="failed to load task YAML"):
        load_task(path)


def test_task_markdown_is_a_freeform_sibling_of_runtime_yaml(tmp_path) -> None:
    task_path = tmp_path / "task.yaml"
    markdown = "# TASK-001\n\n自由記述の作業文脈\n"
    assert task_markdown_path(task_path) == tmp_path / "task.md"
    assert write_task_markdown(task_path, markdown) == tmp_path / "task.md"
    assert load_task_markdown(task_path) == markdown

    with pytest.raises(FlowError, match="failed to load task Markdown"):
        load_task_markdown(tmp_path / "missing.yaml")


def test_builtin_workflow_has_no_task_document_guards() -> None:
    task = _task("TASK-001")
    workflow = task_workflow()
    assert {transition.actor for transition in workflow.transitions} == {"user"}
    assert available_transitions(task, workflow) == ("start_task",)
    assert apply_transition(task, workflow, "start_task").state == "in_progress"
    with pytest.raises(FlowError, match="requirement not satisfied"):
        apply_transition(task, workflow, "cancel_task")


def test_interrupt_and_resume_keep_only_runtime_relations() -> None:
    workflow = task_workflow()
    parent = _task("TASK-001", "in_progress")
    child = update_dependency(_task("TASK-002"), "TASK-003", True)
    completed_dependency = _task("TASK-003", "completed")

    paused, started = interrupt_task(
        parent,
        child,
        {
            parent.id: parent,
            child.id: child,
            completed_dependency.id: completed_dependency,
        },
        workflow,
        "urgent",
    )
    assert (paused.state, paused.interruption_task_id) == ("paused", child.id)
    assert (started.state, started.interruption_source_task_id) == (
        "in_progress",
        parent.id,
    )

    completed_child = started.model_copy(update={"state": "completed"})
    assert (
        resume_task(
            paused,
            {paused.id: paused, completed_child.id: completed_child},
            workflow,
        ).state
        == "in_progress"
    )
