"""Models for the single workspace Operator Terminal."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OperatorTerminalState(StrEnum):
    OFF = "off"
    ON = "on"


class OperatorTerminal(BaseModel):
    """The current lifecycle state of the Operator Terminal."""

    model_config = ConfigDict(extra="forbid")

    state: OperatorTerminalState
    operator_id: str | None = Field(default=None, min_length=1)


class OperatorTerminalRef(BaseModel):
    """An active Operator Terminal selected by its generated identifier."""

    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(min_length=1)
