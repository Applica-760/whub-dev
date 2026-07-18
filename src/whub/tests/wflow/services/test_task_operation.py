"""Task creation and content-operation service tests."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from whub.wflow.models import TaskDocument
from whub.wflow.services import (
    WflowError, append_phase_log, apply_transition, create_task, delete_plan_item,
    insert_plan_step, load_task, load_task_workflow, record_acceptance, update_plan_item,
    update_acceptance, update_dependency, update_step, write_task,
)


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "src/whub/tests/wflow/fixtures/task.yaml"


def _task_data() -> dict:
    return yaml.safe_load(_TASK_PATH.read_text())


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


def test_creates_draft_task_with_next_id_and_standard_path(tmp_path: Path) -> None:
    existing = _task_data(); existing["task"]["id"] = "TASK-014"
    (tmp_path / "existing.yaml").write_text(yaml.safe_dump(existing, allow_unicode=True))
    path, task = create_task(tmp_path, "新しいTask", "目的", ("方針1", "方針2"), now=datetime(2026, 7, 17, 15, 30))
    assert path == tmp_path / "20260717_1530_task-015.yaml"
    assert task.task.id == "TASK-015" and task.task.approach == ["方針1", "方針2"] and task.plan is None
    assert load_task(path) == task


def test_create_task_rejects_existing_target_without_overwriting(tmp_path: Path) -> None:
    target = tmp_path / "20260717_1530_task-001.yaml"; target.write_text("original")
    with pytest.raises(WflowError, match="already exists"):
        create_task(tmp_path, "title", "objective", now=datetime(2026, 7, 17, 15, 30))
    assert target.read_text() == "original"


def test_deletes_pending_plan_items_and_inserts_steps() -> None:
    deleted = delete_plan_item(_draft_task(), "001-001")
    assert deleted.plan.phases[0].steps[0].deleted
    inserted = insert_plan_step(deleted, "追加する", "002-001")
    assert inserted.plan.phases[1].steps[1].description == "追加する"
    phase_inserted = insert_plan_step(inserted, "新PhaseのStep", "001")
    assert phase_inserted.plan.phases[1].title == "挿入フェーズ"


def test_inserts_named_phases_and_steps_in_selected_phases_and_updates_items() -> None:
    named_phase = insert_plan_step(
        _draft_task(),
        "最初のStep",
        phase_title="名前付きPhase",
    )
    assert named_phase.plan.phases[-1].title == "名前付きPhase"
    assert named_phase.plan.phases[-1].steps[0].description == "最初のStep"

    inserted_step = insert_plan_step(named_phase, "追加Step", phase_ref="002")
    assert inserted_step.plan.phases[1].steps[-1].description == "追加Step"

    updated_phase = update_plan_item(inserted_step, "003", "更新済みPhase")
    updated_step = update_plan_item(updated_phase, "002-002", "更新済みStep")
    assert updated_step.plan.phases[2].title == "更新済みPhase"
    assert updated_step.plan.phases[1].steps[1].description == "更新済みStep"


def test_updates_draft_dependencies_and_task_or_phase_acceptance() -> None:
    dependency_added = update_dependency(_draft_task(), "TASK-002", True)
    assert dependency_added.task.depends_on == ["TASK-002"]
    with pytest.raises(WflowError, match="already exists"):
        update_dependency(dependency_added, "TASK-002", True)
    with pytest.raises(WflowError, match="itself"):
        update_dependency(dependency_added, "TASK-001", True)
    dependency_removed = update_dependency(dependency_added, "TASK-002", False)
    assert dependency_removed.task.depends_on == []

    task_acceptance = update_acceptance(dependency_removed, "Taskを検証する", True)
    assert task_acceptance.plan.acceptance[-1].id == "ACC-002"
    phase_acceptance = update_acceptance(task_acceptance, "Phaseを検証する", True, "001")
    assert phase_acceptance.plan.phases[0].acceptance[-1].id == "ACC-003"
    removed = update_acceptance(phase_acceptance, "ACC-002", False)
    assert [item.id for item in removed.plan.acceptance] == ["ACC-001"]


def test_plan_operations_reject_non_draft_and_execution_history() -> None:
    task = _draft_task(); active = apply_transition(task, load_task_workflow(), "approve_plan", "user")
    with pytest.raises(WflowError, match="draft"):
        insert_plan_step(active, "追加する")

    completed_step = update_step(active, load_task_workflow(), "002-001", "done", logs=("done",))
    changed = apply_transition(
        completed_step,
        load_task_workflow(),
        "request_plan_change",
        "agent",
        {"reason": "revise pending work"},
    )
    with pytest.raises(WflowError, match="execution history"):
        update_plan_item(changed, "002-001", "書き換え")


def test_step_log_skip_and_acceptance_operations(tmp_path: Path) -> None:
    workflow = load_task_workflow(); active = apply_transition(_draft_task(), workflow, "approve_plan", "user")
    updated = update_step(active, workflow, "002-001", "done", logs=("first",))
    assert updated.plan.phases[1].steps[0].state == "done"
    logged = append_phase_log(updated, "001", ("second",))
    skipped = update_step(logged, workflow, "001-001", "skipped", "not needed", ("skipped",))
    assert skipped.plan.phases[0].steps[0].skip_reason == "not needed"
    path = tmp_path / "task.yaml"; write_task(path, skipped); assert load_task(path) == skipped
    accepted = record_acceptance(active, "ACC-001", "passed")
    with pytest.raises(WflowError, match="already recorded"):
        record_acceptance(accepted, "ACC-001", "passed")
