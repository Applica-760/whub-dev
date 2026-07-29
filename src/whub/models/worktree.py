"""Models for workspace worktree definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


@dataclass(frozen=True)
class WorktreeDefinitionRecord:
    """One discovered definition and any recoverable diagnostics."""

    path: Path
    definition: WorktreeDefinition | None
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class GitWorktree:
    """One Git worktree entry reported by `git worktree list --porcelain`."""

    path: Path
    branch: str | None


@dataclass(frozen=True)
class WorktreeInspection:
    """One registered definition and its YAML and Git consistency diagnostics."""

    record: WorktreeDefinitionRecord
    diagnostics: tuple[str, ...]

    @property
    def definition(self) -> WorktreeDefinition | None:
        return self.record.definition


@dataclass(frozen=True)
class WorktreeStatus:
    """Read-only worktree state for status and web presentation."""

    parent_project: str | None
    task_id: str | None
    branch: str | None
    workspace_path: str | None
    diagnostics: tuple[str, ...] = ()
