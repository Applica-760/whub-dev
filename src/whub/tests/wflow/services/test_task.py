"""Task checkerの仕様テスト。

検証するケース:
1. 組込みTaskとWorkflowの組合せは整合する。
2. Workflow ID・状態・plan承認の不整合を通知する。
3. Stepの順序違反を通知する。
4. 完了Taskの不足と中止Taskの記録不足を通知する。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from whub.wflow.models import TaskDocument
from whub.wflow.services import (
    WflowError,
    apply_transition,
    available_transitions,
    check_task,
    list_tasks,
    load_task,
    load_task_workflow,
    record_acceptance,
    resolve_task_reference,
    update_step,
    write_task,
)


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "docs/tasks/20260713_2236_whub-task-planning-task-example.yaml"


def _task_data() -> dict:
    return yaml.safe_load(_TASK_PATH.read_text())


def _write_task(root: Path, name: str, data: dict) -> None:
    (root / name).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def _codes(data: dict) -> set[str]:
    task = TaskDocument.model_validate(data)
    return {diagnostic.code for diagnostic in check_task(task, load_task_workflow())}


def test_builtin_task_matches_the_builtin_workflow() -> None:
    # ケース1
    assert _codes(_task_data()) == set()


def test_reports_workflow_state_and_approval_mismatches() -> None:
    # ケース2
    mismatch = _task_data()
    mismatch["task"]["workflow"] = "WF-999"
    assert "workflow_mismatch" in _codes(mismatch)

    unknown_state = _task_data()
    unknown_state["task"]["state"] = "waiting"
    assert "unknown_task_state" in _codes(unknown_state)

    unapproved = _task_data()
    unapproved["task"]["state"] = "in_progress"
    unapproved["approvals"] = []
    assert "missing_plan_approval" in _codes(unapproved)


def test_reports_step_order_violations() -> None:
    # ケース3
    data = _task_data()
    data["plan"]["phases"][0]["steps"][0]["state"] = "pending"

    assert "step_order_violation" in _codes(data)


def test_reports_missing_completion_and_cancellation_records() -> None:
    # ケース4
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
        phase["log"] = None
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

    for phase in task.plan.phases:
        for index, step in enumerate(phase.steps):
            task = update_step(
                task,
                workflow,
                step.id,
                "done",
                log_summary=f"{phase.id} complete" if index == len(phase.steps) - 1 else None,
            )
    task = record_acceptance(task, "ACC-001", "passed", ("verified",))
    assert "complete_task" not in available_transitions(task, workflow)
    assert "complete_task" in available_transitions(task, workflow, {"result": "done"})
    task = apply_transition(task, workflow, "complete_task", "agent", {"result": "done"})
    assert task.task.state == "completed"
    assert task.result.summary == "done"


def test_rejects_wrong_actor_and_out_of_order_step() -> None:
    workflow = load_task_workflow()
    with pytest.raises(WflowError, match="requires actor 'user'"):
        apply_transition(_draft_task(), workflow, "approve_plan", "agent")

    active = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    with pytest.raises(WflowError, match="next step is 'STP-001-001'"):
        update_step(active, workflow, "STP-002-001", "done")

    with pytest.raises(WflowError, match="requires a log summary"):
        update_step(active, workflow, "STP-001-001", "done")


def test_skip_records_its_reason_and_write_is_loadable(tmp_path: Path) -> None:
    workflow = load_task_workflow()
    active = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    skipped = update_step(
        active,
        workflow,
        "STP-001-001",
        "skipped",
        "not needed",
        "phase skipped",
        ("no work required",),
    )
    assert skipped.plan.phases[0].steps[0].skip_reason == "not needed"
    assert skipped.plan.phases[0].log.summary == "phase skipped"

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
