"""Task checkerの仕様テスト。

検証するケース:
1. 組込みTaskとWorkflowの組合せは整合する。
2. 状態・plan承認の不整合を通知する。
3. 完了Taskの不足と中止Taskの記録不足を通知する。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whub.wflow.models import TaskDocument
from whub.wflow.models.task import AcceptanceCriterion
from whub.wflow.services import (
    WflowError,
    append_phase_log,
    apply_transition,
    available_transitions,
    interrupt_task,
    list_tasks,
    load_task,
    load_task_workflow,
    record_acceptance,
    render_task_flow,
    resolve_task_reference,
    resume_task,
    update_step,
    validate_task,
    validate_task_interruption,
    write_task,
)


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


def _task_data() -> dict:
    return yaml.safe_load(_TASK_PATH.read_text())


def _write_task(root: Path, name: str, data: dict) -> None:
    (root / name).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def _codes(data: dict) -> set[str]:
    task = TaskDocument.model_validate(data)
    return {diagnostic.code for diagnostic in validate_task(task, load_task_workflow())}


def test_builtin_task_matches_the_builtin_workflow() -> None:
    # ケース1
    assert _codes(_task_data()) == set()


def test_reports_state_and_approval_mismatches() -> None:
    # ケース2
    unknown_state = _task_data()
    unknown_state["task"]["state"] = "waiting"
    assert "unknown_task_state" in _codes(unknown_state)

    unapproved = _task_data()
    unapproved["task"]["state"] = "in_progress"
    unapproved["approvals"] = []
    assert "missing_plan_approval" in _codes(unapproved)

    paused = _task_data()
    paused["task"]["state"] = "paused"
    paused["approvals"] = []
    assert "missing_plan_approval" in _codes(paused)


def test_reports_missing_completion_and_cancellation_records() -> None:
    # ケース3
    completed = _task_data()
    completed["result"] = None
    completed["acceptance_results"] = []
    completed["plan"]["phases"][1]["steps"][2]["state"] = "pending"
    codes = _codes(completed)
    assert {"incomplete_steps", "missing_result", "unsatisfied_acceptance"} <= codes

    cancelled = _task_data()
    cancelled["task"]["state"] = "cancelled"
    cancelled["cancellation"] = None
    assert "missing_cancellation" in _codes(cancelled)


def _draft_task() -> TaskDocument:
    data = _task_data()
    data["task"]["state"] = "draft"
    data["approvals"] = []
    data["acceptance_results"] = []
    data["change_requests"] = []
    data["result"] = None
    for phase in data["plan"]["phases"]:
        phase["log"] = []
        for step in phase["steps"]:
            step["state"] = "pending"
    return TaskDocument.model_validate(data)


def test_applies_lifecycle_transitions_and_records() -> None:
    workflow = load_task_workflow()
    task = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    assert task.task.state == "in_progress"
    assert task.approvals[-1].actor == "user"

    with pytest.raises(WflowError, match="requirement not satisfied"):
        apply_transition(task, workflow, "complete_task", "agent", {"result": "done"})

    for phase_index, phase in enumerate(task.plan.phases, start=1):
        for step_index, step in enumerate(phase.steps, start=1):
            task = update_step(
                task,
                workflow,
                f"{phase_index:03}-{step_index:03}",
                "done",
                logs=(f"phase {phase_index} complete",)
                if step_index == len(phase.steps)
                else (),
            )
    task = record_acceptance(task, "ACC-001", "passed", ("verified",))
    assert "complete_task" not in available_transitions(task, workflow)
    assert "complete_task" in available_transitions(task, workflow, {"result": "done"})
    task = apply_transition(task, workflow, "complete_task", "agent", {"result": "done"})
    assert task.task.state == "completed"
    assert task.result.summary == "done"


def test_interrupts_and_resumes_with_paused_operation_limits() -> None:
    workflow = load_task_workflow()
    active = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    active = active.model_copy(
        update={
            "task": active.task.model_copy(
                update={
                    "interruption_task_id": "TASK-002",
                    "interruption_reason": "urgent issue",
                }
            )
        }
    )

    with pytest.raises(WflowError, match="requires actor 'agent'"):
        apply_transition(active, workflow, "interrupt_task", "user")

    paused = apply_transition(active, workflow, "interrupt_task", "agent")
    assert paused.task.state == "paused"
    assert available_transitions(paused, workflow) == ("resume_task",)
    assert append_phase_log(paused, "001", ("interruption noted",)).plan.phases[0].log == [
        "interruption noted"
    ]

    with pytest.raises(WflowError, match="paused"):
        update_step(paused, workflow, "001-001", "done")
    with pytest.raises(WflowError, match="paused"):
        record_acceptance(paused, "ACC-001", "passed")
    with pytest.raises(WflowError, match="not allowed from state 'paused'"):
        apply_transition(paused, workflow, "request_plan_change", "agent", {"reason": "later"})
    with pytest.raises(WflowError, match="not allowed from state 'paused'"):
        apply_transition(paused, workflow, "complete_task", "agent", {"result": "done"})

    resumed = apply_transition(paused, workflow, "resume_task", "agent")
    assert resumed.task.state == "in_progress"
    paused_again = apply_transition(resumed, workflow, "interrupt_task", "agent")
    cancelled = apply_transition(paused_again, workflow, "cancel_task", "user", {"reason": "stop"})
    assert cancelled.task.state == "cancelled"


def test_interrupt_operation_requires_terminal_child_before_resume() -> None:
    workflow = load_task_workflow()
    parent = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    child = _draft_task().model_copy(
        update={"task": _draft_task().task.model_copy(update={"id": "TASK-002"})}
    )
    tasks = {parent.task.id: parent, child.task.id: child}

    paused, started = interrupt_task(parent, child, tasks, workflow, "urgent issue")
    assert paused.task.state == "paused"
    assert paused.task.interruption_task_id == started.task.id
    assert paused.task.interruption_reason == "urgent issue"
    assert started.task.state == "in_progress"
    assert started.task.interruption_source_task_id == paused.task.id
    assert started.approvals[-1].actor == "user"

    updated_tasks = {paused.task.id: paused, started.task.id: started}
    with pytest.raises(WflowError, match="not terminal"):
        resume_task(paused, updated_tasks, workflow)

    cancelled_child = apply_transition(started, workflow, "cancel_task", "user", {"reason": "done"})
    resumed = resume_task(
        paused,
        {paused.task.id: paused, cancelled_child.task.id: cancelled_child},
        workflow,
    )
    assert resumed.task.state == "in_progress"


def test_nested_interruptions_resume_in_reverse_order() -> None:
    workflow = load_task_workflow()
    parent = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    child = _draft_task().model_copy(
        update={"task": _draft_task().task.model_copy(update={"id": "TASK-002"})}
    )
    grandchild = _draft_task().model_copy(
        update={"task": _draft_task().task.model_copy(update={"id": "TASK-003"})}
    )

    paused_parent, active_child = interrupt_task(
        parent,
        child,
        {parent.task.id: parent, child.task.id: child, grandchild.task.id: grandchild},
        workflow,
        "first interruption",
    )
    paused_child, active_grandchild = interrupt_task(
        active_child,
        grandchild,
        {
            paused_parent.task.id: paused_parent,
            active_child.task.id: active_child,
            grandchild.task.id: grandchild,
        },
        workflow,
        "second interruption",
    )

    cancelled_grandchild = apply_transition(
        active_grandchild, workflow, "cancel_task", "user", {"reason": "resolved"}
    )
    resumed_child = resume_task(
        paused_child,
        {
            paused_parent.task.id: paused_parent,
            paused_child.task.id: paused_child,
            cancelled_grandchild.task.id: cancelled_grandchild,
        },
        workflow,
    )
    cancelled_child = apply_transition(
        resumed_child, workflow, "cancel_task", "user", {"reason": "resolved"}
    )
    resumed_parent = resume_task(
        paused_parent,
        {
            paused_parent.task.id: paused_parent,
            cancelled_child.task.id: cancelled_child,
            cancelled_grandchild.task.id: cancelled_grandchild,
        },
        workflow,
    )

    assert resumed_child.task.state == "in_progress"
    assert resumed_parent.task.state == "in_progress"


def test_validates_interruption_relationships() -> None:
    parent_data = _task_data()
    parent_data["task"].update(
        state="paused",
        interruption_task_id="TASK-002",
        interruption_reason="urgent issue",
    )
    child_data = _task_data()
    child_data["task"].update(
        id="TASK-002",
        state="in_progress",
        interruption_source_task_id="TASK-001",
    )
    parent = TaskDocument.model_validate(parent_data)
    child = TaskDocument.model_validate(child_data)
    tasks = {parent.task.id: parent, child.task.id: child}

    assert validate_task_interruption(parent, tasks) == ()
    assert validate_task_interruption(child, tasks) == ()

    second_child_data = _task_data()
    second_child_data["task"].update(
        id="TASK-003",
        state="in_progress",
        interruption_source_task_id="TASK-001",
    )
    second_child = TaskDocument.model_validate(second_child_data)
    diagnostics = validate_task_interruption(parent, {**tasks, second_child.task.id: second_child})
    assert {item.code for item in diagnostics} == {"multiple_active_interruptions"}

    child_data["task"]["interruption_source_task_id"] = "TASK-999"
    mismatched_child = TaskDocument.model_validate(child_data)
    diagnostics = validate_task_interruption(parent, {parent.task.id: parent, mismatched_child.task.id: mismatched_child})
    assert {item.code for item in diagnostics} == {"interruption_link_mismatch"}


def test_rejects_wrong_actor_and_invalid_step_reference() -> None:
    workflow = load_task_workflow()
    with pytest.raises(WflowError, match="requires actor 'user'"):
        apply_transition(_draft_task(), workflow, "approve_plan", "agent")

    active = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    with pytest.raises(WflowError, match="must be PPP-SSS"):
        update_step(active, workflow, "2-1", "done")

    with pytest.raises(WflowError, match="requires a log"):
        update_step(active, workflow, None, "done")


def test_updates_selected_step_out_of_order() -> None:
    workflow = load_task_workflow()
    active = apply_transition(_draft_task(), workflow, "approve_plan", "user")

    updated = update_step(
        active,
        workflow,
        "002-001",
        "done",
        logs=("first finding", "second finding"),
    )

    assert updated.plan.phases[1].steps[0].state == "done"
    assert updated.plan.phases[1].log == ["first finding", "second finding"]
    assert validate_task(updated, workflow) == ()


def test_appends_multiple_lines_to_a_phase_log() -> None:
    workflow = load_task_workflow()
    active = apply_transition(_draft_task(), workflow, "approve_plan", "user")

    logged = append_phase_log(active, "001", ("first finding", "second finding"))

    assert logged.plan.phases[0].log == ["first finding", "second finding"]
    with pytest.raises(WflowError, match="phase reference must be PPP"):
        append_phase_log(active, "1", ("invalid",))
    with pytest.raises(WflowError, match="in_progress or paused"):
        append_phase_log(_draft_task(), "001", ("invalid",))


def test_skip_records_its_reason_and_write_is_loadable(tmp_path: Path) -> None:
    workflow = load_task_workflow()
    active = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    skipped = update_step(
        active,
        workflow,
        None,
        "skipped",
        "not needed",
        ("phase skipped", "no work required"),
    )
    assert skipped.plan.phases[0].steps[0].skip_reason == "not needed"
    assert skipped.plan.phases[0].log == ["phase skipped", "no work required"]

    path = tmp_path / "task.yaml"
    write_task(path, skipped)
    assert load_task(path) == skipped


def test_rejects_duplicate_acceptance_results() -> None:
    task = _draft_task()
    workflow = load_task_workflow()
    active = apply_transition(task, workflow, "approve_plan", "user")
    accepted = record_acceptance(active, "ACC-001", "passed")

    with pytest.raises(WflowError, match="already recorded"):
        record_acceptance(accepted, "ACC-001", "passed")


def test_lists_tasks_with_dependency_status_and_invalid_records(tmp_path: Path) -> None:
    prerequisite = _task_data()
    dependent = _task_data()
    dependent["task"].update(
        id="TASK-003",
        title="depends on TASK-001",
        state="draft",
        depends_on=["TASK-001"],
    )
    _write_task(tmp_path, "prerequisite.yaml", prerequisite)
    (tmp_path / "nested").mkdir(exist_ok=True)
    _write_task(tmp_path / "nested", "dependent.yaml", dependent)
    (tmp_path / "broken.yaml").write_text("schema_version: [")

    tasks = {item.path: item for item in list_tasks(tmp_path)}

    assert tasks["prerequisite.yaml"].ready is False
    assert tasks["nested/dependent.yaml"].ready is True
    assert tasks["broken.yaml"].state is None
    assert tasks["broken.yaml"].diagnostics
    assert "\n" not in tasks["broken.yaml"].diagnostics[0]


def test_lists_interruption_relationships_and_resumability(tmp_path: Path) -> None:
    parent = _task_data()
    parent["task"].update(
        state="paused",
        interruption_task_id="TASK-002",
        interruption_reason="urgent issue",
    )
    parent["result"] = None
    child = _task_data()
    child["task"].update(id="TASK-002", interruption_source_task_id="TASK-001")
    _write_task(tmp_path, "parent.yaml", parent)
    _write_task(tmp_path, "child.yaml", child)

    tasks = {item.id: item for item in list_tasks(tmp_path)}

    assert tasks["TASK-001"].interruption_task_id == "TASK-002"
    assert tasks["TASK-001"].interruption_reason == "urgent issue"
    assert tasks["TASK-001"].resumable is True
    assert tasks["TASK-002"].interruption_source_task_id == "TASK-001"


def test_lists_missing_and_duplicate_dependencies_as_blocked(tmp_path: Path) -> None:
    first = _task_data()
    second = _task_data()
    second["task"]["title"] = "duplicate TASK-001"
    dependent = _task_data()
    dependent["task"].update(
        id="TASK-003",
        title="blocked task",
        state="draft",
        depends_on=["TASK-001", "TASK-999"],
    )
    _write_task(tmp_path, "first.yaml", first)
    _write_task(tmp_path, "second.yaml", second)
    _write_task(tmp_path, "dependent.yaml", dependent)

    tasks = {item.path: item for item in list_tasks(tmp_path)}

    assert "duplicate task id: TASK-001" in tasks["first.yaml"].diagnostics
    assert "duplicate task id: TASK-001" in tasks["second.yaml"].diagnostics
    assert tasks["dependent.yaml"].blocked_by == [
        "ambiguous dependency: TASK-001",
        "missing dependency: TASK-999",
    ]
    assert tasks["dependent.yaml"].ready is False


def test_renders_task_flow_with_phase_and_task_acceptance() -> None:
    task = _draft_task()
    task.plan.phases[0].acceptance = [
        AcceptanceCriterion(id="ACC-002", statement="first phase is verified")
    ]

    graph = render_task_flow(task)

    assert 'phase_001["Phase 1: 現行手順の確認"]' in graph
    assert 'phase_002["Phase 2: README更新と検証"]' in graph
    assert "phase_001 --> phase_002" in graph
    assert 'phase_001_ACC_002["ACC-002: first phase is verified"]' in graph
    assert "phase_001 --> phase_001_ACC_002" in graph
    assert 'task_ACC_001["ACC-001:' in graph
    assert "phase_002 --> task_ACC_001" in graph


def test_resolves_task_ids_and_rejects_missing_or_ambiguous_ids(tmp_path: Path) -> None:
    first = _task_data()
    first_path = tmp_path / "first.yaml"
    _write_task(tmp_path, first_path.name, first)

    assert resolve_task_reference("TASK-001", tmp_path) == first_path
    assert resolve_task_reference("001", tmp_path) == first_path
    with pytest.raises(WflowError, match="task ID not found: TASK-999"):
        resolve_task_reference("TASK-999", tmp_path)

    duplicate = _task_data()
    duplicate["task"]["title"] = "duplicate TASK-001"
    _write_task(tmp_path, "duplicate.yaml", duplicate)

    with pytest.raises(WflowError, match="task ID is ambiguous: TASK-001"):
        resolve_task_reference("TASK-001", tmp_path)
