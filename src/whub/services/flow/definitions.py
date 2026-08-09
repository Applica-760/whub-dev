"""Built-in Flow definitions."""

from __future__ import annotations

from whub.models.flow import WorkflowDefinition


_TASK_WORKFLOW = {
    "schema_version": 1,
    "workflow": {
        "id": "WF-001",
        "name": "task",
        "initial_state": "draft",
        "terminal_states": ["completed", "cancelled"],
    },
    "states": ["draft", "in_progress", "paused", "completed", "cancelled"],
    "transitions": [
        {
            "trigger": "start_task",
            "actor": "user",
            "from": "draft",
            "to": "in_progress",
        },
        {
            "trigger": "interrupt_task",
            "actor": "user",
            "from": "in_progress",
            "to": "paused",
        },
        {
            "trigger": "resume_task",
            "actor": "user",
            "from": "paused",
            "to": "in_progress",
        },
        {
            "trigger": "complete_task",
            "actor": "user",
            "from": "in_progress",
            "to": "completed",
        },
        {
            "trigger": "cancel_task",
            "actor": "user",
            "from": ["draft", "in_progress", "paused"],
            "to": "cancelled",
            "requires": [{"field": "$input.reason", "operator": "exists"}],
        },
    ],
}


def task_workflow() -> WorkflowDefinition:
    return WorkflowDefinition.model_validate(_TASK_WORKFLOW)
