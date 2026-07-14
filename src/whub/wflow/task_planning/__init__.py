"""Public API and built-in Workflow for task-planning."""

from importlib.resources import as_file, files

from whub.wflow.task_planning.models import (
    AcceptanceCriterion,
    AcceptanceResult,
    ChangeRequest,
    PlanApproval,
    PlanPhase,
    PlanStep,
    TaskPlan,
    TaskPlanningDocument,
    TaskPlanningError,
    load_task_planning,
)
from whub.wflow.workflow import WorkflowDefinition, load_workflow


def load_task_planning_workflow() -> WorkflowDefinition:
    resource = files("whub.wflow.task_planning").joinpath("workflow.yaml")
    with as_file(resource) as path:
        return load_workflow(path)


__all__ = [
    "AcceptanceCriterion",
    "AcceptanceResult",
    "ChangeRequest",
    "PlanApproval",
    "PlanPhase",
    "PlanStep",
    "TaskPlan",
    "TaskPlanningDocument",
    "TaskPlanningError",
    "load_task_planning",
    "load_task_planning_workflow",
]
