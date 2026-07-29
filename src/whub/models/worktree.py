"""Models for workspace worktree definitions."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from whub.wflow.models.task import TASK_ID_PATTERN

TaskId = Annotated[str, Field(pattern=TASK_ID_PATTERN)]
ProjectName = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]


class WorktreeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorktreeDefinition(WorktreeModel):
    schema_version: Literal[1] = 1
    task_id: TaskId
    parent_project: ProjectName
    branch: str
    workspace_path: str

    @model_validator(mode="after")
    def _validate_identity(self) -> WorktreeDefinition:
        number = self.task_id.removeprefix("TASK-")
        expected_name = f"{self.parent_project}-{number}"
        expected_branch = f"tasks/{number}"
        expected_workspace_path = f"projects/worktrees/{expected_name}"
        if self.branch != expected_branch:
            raise ValueError(f"branch must be {expected_branch}")
        if self.workspace_path != expected_workspace_path:
            raise ValueError(f"workspace_path must be {expected_workspace_path}")
        return self
