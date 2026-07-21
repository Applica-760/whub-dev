"""Workflow定義の意味検査の仕様テスト。

検証するケース:
1. 組込みWorkflowに意味エラーがない。
2. 初期状態から到達できない状態を通知する。
3. 終端状態へ到達できない状態を通知する。
4. 同じ状態からのtrigger曖昧性を通知する。
5. 終端状態からの遷移を通知する。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from whub.wflow.models import WorkflowDefinition
from whub.wflow.services import check_workflow, load_task_workflow
from whub.wflow.services.workflow import apply_transition, available_transitions


_ROOT = Path(__file__).parents[5]
_WORKFLOW_PATH = _ROOT / "src/whub/wflow/definitions/task.yaml"


def _workflow_data() -> dict:
    return yaml.safe_load(_WORKFLOW_PATH.read_text())


def _codes(workflow: WorkflowDefinition) -> set[str]:
    return {diagnostic.code for diagnostic in check_workflow(workflow)}


def test_builtin_workflow_has_no_semantic_errors() -> None:
    # ケース1
    assert check_workflow(load_task_workflow()) == ()


def test_reports_unreachable_states() -> None:
    # ケース2
    data = _workflow_data()
    data["states"].append("orphan")

    assert "unreachable_state" in _codes(WorkflowDefinition.model_validate(data))


def test_reports_nonterminal_states_without_a_terminal_path() -> None:
    # ケース3
    data = _workflow_data()
    data["states"].append("loop")
    data["transitions"].append(
        {"trigger": "repeat", "actor": "agent", "from": "loop", "to": "loop"}
    )

    assert "no_terminal_path" in _codes(WorkflowDefinition.model_validate(data))


def test_reports_ambiguous_triggers_from_the_same_state() -> None:
    # ケース4
    data = _workflow_data()
    data["transitions"].append(
        {
            "trigger": "approve_plan",
            "actor": "user",
            "from": "draft",
            "to": "cancelled",
        }
    )

    assert "ambiguous_trigger" in _codes(WorkflowDefinition.model_validate(data))


def test_reports_transitions_from_terminal_states() -> None:
    # ケース5
    data = _workflow_data()
    data["transitions"].append(
        {
            "trigger": "reopen",
            "actor": "user",
            "from": "completed",
            "to": "in_progress",
        }
    )

    assert "terminal_state_has_transition" in _codes(
        WorkflowDefinition.model_validate(data)
    )


def test_applies_a_domain_independent_transition() -> None:
    workflow = WorkflowDefinition.model_validate(
        {
            "schema_version": 1,
            "workflow": {
                "id": "WF-002",
                "name": "generic",
                "initial_state": "draft",
                "terminal_states": ["completed"],
            },
            "states": ["draft", "completed"],
            "transitions": [
                {
                    "trigger": "complete",
                    "actor": "user",
                    "from": "draft",
                    "to": "completed",
                    "requires": [{"field": "$input.summary", "operator": "exists"}],
                    "records": [
                        {
                            "field": "history",
                            "value": {"summary": "$input.summary", "actor": "$actor"},
                        }
                    ],
                }
            ],
        }
    )
    data = {"history": []}

    assert available_transitions(workflow, "draft", data) == ()
    state, updated = apply_transition(
        workflow,
        "draft",
        data,
        "complete",
        "user",
        {"summary": "done"},
    )

    assert state == "completed"
    assert updated == {"history": [{"summary": "done", "actor": "user"}]}
