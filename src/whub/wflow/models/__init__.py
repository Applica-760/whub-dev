"""Pydantic models for wflow definitions and task records."""

from whub.wflow.models.task import TaskDocument
from whub.wflow.models.workflow import WorkflowDefinition

__all__ = [
    "TaskDocument",
    "WorkflowDefinition",
]
