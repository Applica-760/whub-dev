"""Generic models for declarative Workflow definitions."""
from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NonEmptyStr = Annotated[str, Field(min_length=1)]
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
StateName = Identifier
type JsonValue = (
    str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
)


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
    operator: Literal["exists", "all_in", "satisfied_if_defined"]
    value: JsonValue = None
    result_field: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _validate_operator_fields(self) -> TransitionRequirement:
        if self.operator == "all_in" and not isinstance(self.value, list):
            raise ValueError("all_in requires value")
        if self.operator == "satisfied_if_defined" and self.result_field is None:
            raise ValueError("satisfied_if_defined requires result_field")
        return self


class TransitionRecord(WorkflowModel):
    field: NonEmptyStr
    value: JsonValue


class WorkflowTransition(WorkflowModel):
    trigger: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    actor: Identifier
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
