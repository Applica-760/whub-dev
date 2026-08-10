"""Generic models for declarative Flow definitions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


NonEmptyStr = Annotated[str, Field(min_length=1)]
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
StateName = Identifier
TASK_ID_PATTERN = r"^TASK-[0-9]+$"


class WorkflowModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class WorkflowHeader(WorkflowModel):
    id: str = Field(pattern=r"^WF-[0-9]+$")
    name: NonEmptyStr
    initial_state: StateName
    terminal_states: list[StateName] = Field(min_length=1)


class TransitionRequirement(WorkflowModel):
    field: NonEmptyStr
    operator: Literal["exists", "all_in", "satisfied_if_defined", "active_steps_all_in"]
    value: JsonValue = None
    result_field: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _validate_operator_fields(self) -> TransitionRequirement:
        if self.operator in {"all_in", "active_steps_all_in"} and not isinstance(
            self.value, list
        ):
            raise ValueError(f"{self.operator} requires a list value")
        if self.operator == "satisfied_if_defined" and self.result_field is None:
            raise ValueError("satisfied_if_defined requires result_field")
        return self


class TransitionRecord(WorkflowModel):
    field: NonEmptyStr
    value: JsonValue


class WorkflowTransition(WorkflowModel):
    trigger: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    from_: StateName | Annotated[list[StateName], Field(min_length=1)] = Field(
        alias="from"
    )
    to: StateName
    requires: list[TransitionRequirement] = Field(default_factory=list)
    records: list[TransitionRecord] = Field(default_factory=list)

    @property
    def source_states(self) -> list[str]:
        if isinstance(self.from_, str):
            return [self.from_]
        return self.from_


class WorkflowDefinition(WorkflowModel):
    schema_version: Literal[1]
    workflow: WorkflowHeader
    states: list[StateName] = Field(min_length=1)
    transitions: list[WorkflowTransition] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_state_references(self) -> WorkflowDefinition:
        counts = Counter(self.states)
        duplicates = sorted(state for state, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate workflow states: {', '.join(duplicates)}")

        referenced = {
            self.workflow.initial_state,
            *self.workflow.terminal_states,
            *(transition.to for transition in self.transitions),
            *(
                state
                for transition in self.transitions
                for state in transition.source_states
            ),
        }
        unknown = sorted(referenced - set(self.states))
        if unknown:
            raise ValueError(f"unknown workflow states: {', '.join(unknown)}")
        return self


class TaskRuntime(WorkflowModel):
    """Minimal runtime state for one Task Flow instance."""

    schema_version: Literal[2]
    id: str = Field(pattern=TASK_ID_PATTERN)
    workflow: str = Field(pattern=r"^WF-[0-9]+$")
    state: StateName
    depends_on: list[Annotated[str, Field(pattern=TASK_ID_PATTERN)]] = Field(
        default_factory=list
    )
    interruption_task_id: Annotated[str, Field(pattern=TASK_ID_PATTERN)] | None = None
    interruption_source_task_id: (
        Annotated[str, Field(pattern=TASK_ID_PATTERN)] | None
    ) = None
    legacy: bool = Field(default=False, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_schema_v1(cls, value: object) -> object:
        if not isinstance(value, Mapping) or value.get("schema_version") != 1:
            return value
        task = value.get("task")
        if not isinstance(task, Mapping):
            return value
        return {
            "schema_version": 2,
            "id": task.get("id"),
            "workflow": "WF-001",
            "state": task.get("state"),
            "depends_on": task.get("depends_on", []),
            "interruption_task_id": task.get("interruption_task_id"),
            "interruption_source_task_id": task.get("interruption_source_task_id"),
            "legacy": True,
        }

    @model_validator(mode="after")
    def _validate_relations(self) -> TaskRuntime:
        if self.id in {self.interruption_task_id, self.interruption_source_task_id}:
            raise ValueError("task cannot interrupt itself")
        return self
