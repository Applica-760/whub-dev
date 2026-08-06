"""Models for workspace worktree definitions."""

from __future__ import annotations

from collections.abc import Mapping
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
    schema_version: Literal[2] = 2
    task_id: TaskId
    parent_project: ProjectName
    branch: str

    @model_validator(mode="before")
    @classmethod
    def _normalize_schema_v1(cls, value: object) -> object:
        if not isinstance(value, Mapping) or value.get("schema_version") != 1:
            return value
        task_id = value.get("task_id")
        parent_project = value.get("parent_project")
        if not isinstance(task_id, str) or not isinstance(parent_project, str):
            return value
        number = task_id.removeprefix("TASK-")
        expected = f"projects/worktrees/{parent_project}-{number}"
        if value.get("workspace_path") != expected:
            raise ValueError(f"workspace_path must be {expected}")
        normalized = dict(value)
        normalized["schema_version"] = 2
        del normalized["workspace_path"]
        return normalized

    @property
    def workspace_path(self) -> str:
        """Return the conventional local path for display-only callers."""
        number = self.task_id.removeprefix("TASK-")
        return f"projects/worktrees/{self.parent_project}-{number}"

    @model_validator(mode="after")
    def _validate_identity(self) -> WorktreeDefinition:
        number = self.task_id.removeprefix("TASK-")
        expected_branch = f"tasks/{number}"
        if self.branch != expected_branch:
            raise ValueError(f"branch must be {expected_branch}")
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
