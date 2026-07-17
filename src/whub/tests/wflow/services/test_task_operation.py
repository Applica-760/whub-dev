"""Task creation and content-operation service tests."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from whub.wflow.models import TaskDocument
from whub.wflow.services import (
    WflowError, append_phase_log, apply_transition, create_task, delete_plan_item,
    insert_plan_step, load_task, load_task_workflow, record_acceptance, update_step, write_task,
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


def test_plan_operations_reject_non_draft_and_execution_history() -> None:
    task = _draft_task(); active = apply_transition(task, load_task_workflow(), "approve_plan", "user")
    with pytest.raises(WflowError, match="draft"):
        insert_plan_step(active, "追加する")


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
