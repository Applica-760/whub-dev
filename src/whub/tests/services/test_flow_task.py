"""Task Flow runtime contract tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from whub.models.flow import TaskRuntime
from whub.services.flow.definitions import task_workflow
from whub.services.flow.errors import FlowError
from whub.services.flow.task.application import (
    cancel_task as cancel_persisted_task,
    complete_task as complete_persisted_task,
    interrupt as interrupt_persisted_task,
    resume as resume_persisted_task,
    start_task as start_persisted_task,
)
from whub.services.flow.task.common import (
    archive_task,
    create_task,
    load_task,
    load_task_markdown,
    task_markdown_path,
    write_task,
    write_task_markdown,
)
from whub.services.flow.task.log import append_task_log
from whub.services.flow.task.query import load_task_records
from whub.services.flow.task.relation import (
    interrupt_task,
    resume_task,
    update_dependency,
)
from whub.services.flow.task.transition import apply_transition
from whub.services.flow.workflow import available_transitions


def _task(task_id: str, state: str = "draft") -> TaskRuntime:
    return TaskRuntime(schema_version=2, id=task_id, workflow="WF-001", state=state)


def _write_pair(path, task: TaskRuntime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_task(path, task)
    write_task_markdown(path, f"# {task.id}\n")


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


def test_create_task_writes_runtime_yaml_and_markdown_pair(tmp_path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    archived = _task("TASK-004", "completed")
    write_task(archive / "archived.yaml", archived)
    write_task_markdown(archive / "archived.yaml", "# archived\n")

    path, task = create_task(
        tmp_path / "active",
        "Title",
        "Objective",
        ("First approach",),
        now=datetime(2026, 8, 9, 12, 34),
        id_roots=(archive,),
    )
    assert path.name == "20260809_1234_task-005.yaml"
    assert task == _task("TASK-005")
    assert load_task(path) == task
    assert (
        load_task_markdown(path)
        == "# Title\n\n## Objective\n\nObjective\n\n## Approach\n\n- First approach\n"
    )


def test_task_log_appends_validated_json_to_markdown(tmp_path) -> None:
    path = tmp_path / "task.yaml"
    write_task_markdown(path, "# Task\n")

    append_task_log(
        path,
        '{"fact":"verified"}',
        "agent",
        now=datetime(2026, 8, 9, 12, 34, 56),
    )
    assert load_task_markdown(path) == (
        "# Task\n\n<!-- whub:task-log:start -->\n"
        "- 2026-08-09T12:34:56 | agent | fact | verified\n"
        "<!-- whub:task-log:end -->\n"
    )

    with pytest.raises(FlowError, match="one LogKind key"):
        append_task_log(path, '{"unknown":"no"}', "agent")


def test_load_task_records_reads_unique_valid_pairs_across_roots(tmp_path) -> None:
    active = tmp_path / "active"
    archive = tmp_path / "archive"
    _write_pair(active / "active.yaml", _task("TASK-001"))
    _write_pair(archive / "archived.yaml", _task("TASK-002", "completed"))

    records = load_task_records(active, archive)
    assert {task_id: path.name for task_id, (path, _) in records.items()} == {
        "TASK-001": "active.yaml",
        "TASK-002": "archived.yaml",
    }


def test_load_task_records_rejects_duplicates_and_invalid_pairs(tmp_path) -> None:
    active = tmp_path / "active"
    archive = tmp_path / "archive"
    _write_pair(active / "active.yaml", _task("TASK-001"))
    _write_pair(archive / "archived.yaml", _task("TASK-001", "completed"))
    with pytest.raises(FlowError, match="duplicate task id"):
        load_task_records(active, archive)

    _write_pair(active / "paused.yaml", _task("TASK-002", "paused"))
    with pytest.raises(FlowError, match="task set is invalid"):
        load_task_records(active)


def test_persisted_runtime_operations_update_and_archive_pairs(tmp_path) -> None:
    active = tmp_path / "active"
    archive = tmp_path / "archive"
    _write_pair(active / "parent.yaml", _task("TASK-001"))
    _write_pair(active / "child.yaml", _task("TASK-002"))

    assert start_persisted_task(active, "001").state == "in_progress"
    paused, started = interrupt_persisted_task(active, "001", "002", "urgent")
    assert (paused.state, started.state) == ("paused", "in_progress")
    assert "interrupted by TASK-002: urgent" in load_task_markdown(
        active / "parent.yaml"
    )

    assert complete_persisted_task(active, archive, "002") == archive / "child.yaml"
    assert resume_persisted_task(active, "001", archive).state == "in_progress"

    _write_pair(active / "cancel.yaml", _task("TASK-003"))
    assert cancel_persisted_task(active, archive, "003", "superseded", archive) == (
        archive / "cancel.yaml"
    )
    assert "cancelled: superseded" in load_task_markdown(archive / "cancel.yaml")


def test_archive_moves_task_yaml_and_markdown_together(tmp_path) -> None:
    source = tmp_path / "active" / "task.yaml"
    source.parent.mkdir()
    task = _task("TASK-001", "completed")
    write_task(source, task)
    write_task_markdown(source, "# completed\n")

    archived = archive_task(source, task, tmp_path / "archive")
    assert archived == tmp_path / "archive" / "task.yaml"
    assert load_task(archived) == task
    assert load_task_markdown(archived) == "# completed\n"
    assert not source.exists()
    assert not task_markdown_path(source).exists()


def test_archive_keeps_active_yaml_when_markdown_is_missing(tmp_path) -> None:
    source = tmp_path / "task.yaml"
    task = _task("TASK-001", "completed")
    write_task(source, task)

    with pytest.raises(FlowError, match="failed to archive task Markdown"):
        archive_task(source, task, tmp_path / "archive")
    assert load_task(source) == task
    assert not (tmp_path / "archive" / "task.yaml").exists()


def test_archive_rolls_back_yaml_when_destination_markdown_exists(tmp_path) -> None:
    source = tmp_path / "task.yaml"
    task = _task("TASK-001", "completed")
    write_task(source, task)
    write_task_markdown(source, "# active\n")
    destination_root = tmp_path / "archive"
    destination_root.mkdir()
    (destination_root / "task.md").write_text("# existing\n")

    with pytest.raises(FlowError, match="archived task already exists"):
        archive_task(source, task, destination_root)
    assert load_task(source) == task
    assert load_task_markdown(source) == "# active\n"
    assert not (destination_root / "task.yaml").exists()
    assert (destination_root / "task.md").read_text() == "# existing\n"


def test_builtin_workflow_has_no_task_document_guards() -> None:
    task = _task("TASK-001")
    workflow = task_workflow()
    assert {transition.actor for transition in workflow.transitions} == {"user"}
    assert available_transitions(
        workflow, task.state, task.model_dump(mode="python")
    ) == ("start_task",)
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
