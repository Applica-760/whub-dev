"""Task checkerの仕様テスト。

検証するケース:
1. 組込みTaskとWorkflowの組合せは整合する。
2. Workflow ID・状態・現在plan承認の不整合を通知する。
3. Stepの順序違反を通知する。
4. 完了Taskの不足と中止Taskの記録不足を通知する。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from whub.wflow.models import TaskDocument
from whub.wflow.services import check_task, load_task_workflow


_ROOT = Path(__file__).parents[5]
_TASK_PATH = _ROOT / "docs/tasks/20260713_2236_whub-task-planning-task-example.yaml"


def _task_data() -> dict:
    return yaml.safe_load(_TASK_PATH.read_text())


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
