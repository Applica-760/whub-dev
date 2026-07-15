"""Workflow・Task YAMLモデルとserviceの仕様テスト。

検証するケース:
1. 雛形のWorkflow・Task YAMLを読み込める。
2. Workflowのactorは特定の役割名へ固定しない。
3. 未知フィールドと不正IDを拒否する。
4. Workflow内の状態重複と状態参照切れを拒否する。
5. 条件operatorごとの必須フィールド不足を拒否する。
6. Task内のID重複とStep IDの親Phase不一致を拒否する。
7. Task内の受け入れ条件参照切れとplan revision範囲外を拒否する。
8. loaderはファイル・YAML・schema不正をWflowErrorにする。

検証しないケース:
1. WorkflowとTaskをまたぐ状態・Workflow IDの整合性。
2. 状態の到達可能性、条件式評価、状態遷移操作。
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from whub.wflow.models import TaskDocument, WorkflowDefinition
from whub.wflow.services import (
    WflowError,
    load_task,
    load_task_workflow,
    load_workflow,
)


_ROOT = Path(__file__).parents[5]
_WORKFLOW_PATH = _ROOT / "src/whub/wflow/definitions/task.yaml"
_TASK_PATH = _ROOT / "docs/tasks/20260713_2236_whub-task-planning-task-example.yaml"


def _workflow_data() -> dict:
    return yaml.safe_load(_WORKFLOW_PATH.read_text())


def _task_data() -> dict:
    return yaml.safe_load(_TASK_PATH.read_text())


def test_loads_workflow_and_task_definitions() -> None:
    workflow = load_task_workflow()
    task = load_task(_TASK_PATH)

    assert workflow.workflow.id == "WF-001"
    assert task.task.id == "TASK-001"
    assert task.plan.revision == 2


def test_workflow_actor_accepts_arbitrary_role_names() -> None:
    data = _workflow_data()
    data["transitions"][0]["actor"] = "reviewer"

    assert WorkflowDefinition.model_validate(data).transitions[0].actor == "reviewer"


def test_rejects_unknown_fields_and_invalid_ids() -> None:
    workflow_data = _workflow_data()
    workflow_data["workflow"]["summary"] = "unsupported"
    with pytest.raises(ValidationError):
        WorkflowDefinition.model_validate(workflow_data)

    task_data = _task_data()
    task_data["task"]["id"] = "INVALID-001"
    with pytest.raises(ValidationError):
        TaskDocument.model_validate(task_data)


def test_rejects_duplicate_and_unknown_workflow_states() -> None:
    duplicate = _workflow_data()
    duplicate["states"].append(duplicate["states"][0])
    with pytest.raises(ValidationError, match="duplicate workflow states"):
        WorkflowDefinition.model_validate(duplicate)

    for mutate in (
        lambda data: data["workflow"].update(initial_state="missing"),
        lambda data: data["workflow"]["terminal_states"].append("missing"),
        lambda data: data["transitions"][0].update(to="missing"),
    ):
        invalid = _workflow_data()
        mutate(invalid)
        with pytest.raises(ValidationError, match="unknown workflow states"):
            WorkflowDefinition.model_validate(invalid)


def test_rejects_missing_operator_fields() -> None:
    all_in = _workflow_data()
    complete = next(
        transition
        for transition in all_in["transitions"]
        if transition["trigger"] == "complete_task"
    )
    complete["requires"][0].pop("value")
    with pytest.raises(ValidationError, match="all_in requires a list value"):
        WorkflowDefinition.model_validate(all_in)

    satisfied = _workflow_data()
    complete = next(
        transition
        for transition in satisfied["transitions"]
        if transition["trigger"] == "complete_task"
    )
    complete["requires"][1].pop("result_field")
    with pytest.raises(ValidationError, match="satisfied_if_defined requires result_field"):
        WorkflowDefinition.model_validate(satisfied)


def test_rejects_duplicate_ids_and_step_parent_mismatch() -> None:
    duplicate = _task_data()
    duplicate["plan"]["phases"].append(
        copy.deepcopy(duplicate["plan"]["phases"][0])
    )
    with pytest.raises(ValidationError, match="duplicate task-planning ids"):
        TaskDocument.model_validate(duplicate)

    mismatch = _task_data()
    mismatch["plan"]["phases"][0]["steps"][0]["id"] = "STP-999-001"
    with pytest.raises(ValidationError, match="does not belong to phase"):
        TaskDocument.model_validate(mismatch)


def test_rejects_unknown_acceptance_and_future_revisions() -> None:
    unknown_acceptance = _task_data()
    unknown_acceptance["acceptance_results"][0]["acceptance"] = "ACC-999"
    with pytest.raises(ValidationError, match="unknown acceptance ids"):
        TaskDocument.model_validate(unknown_acceptance)

    future_revision = _task_data()
    future_revision["approvals"][0]["plan_revision"] = 3
    with pytest.raises(ValidationError, match="future plan revisions"):
        TaskDocument.model_validate(future_revision)

    unknown_log_phase = _task_data()
    unknown_log_phase["logs"] = [{"phase": "PHA-999", "summary": "missing"}]
    with pytest.raises(ValidationError, match="unknown log phases"):
        TaskDocument.model_validate(unknown_log_phase)


def test_loaders_report_file_yaml_and_schema_errors(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(WflowError, match="failed to load Workflow YAML"):
        load_workflow(missing)
    with pytest.raises(WflowError, match="failed to load task YAML"):
        load_task(missing)

    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("schema_version: [")
    with pytest.raises(WflowError, match="failed to load Workflow YAML"):
        load_workflow(invalid)

    invalid.write_text("schema_version: 1\n")
    with pytest.raises(WflowError, match="failed to load task YAML"):
        load_task(invalid)
