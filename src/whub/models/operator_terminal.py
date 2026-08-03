"""Models for workspace-wide Operator Terminals."""

from pydantic import BaseModel, ConfigDict, Field


class OperatorTerminal(BaseModel):
    """One running workspace-wide terminal selected by its identifier."""

    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(min_length=1)


class OperatorTerminals(BaseModel):
    """The active workspace-wide terminals in display order."""

    model_config = ConfigDict(extra="forbid")

    terminals: list[OperatorTerminal]


class OperatorTerminalRef(BaseModel):
    """An active Operator Terminal selected by its generated identifier."""

    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(min_length=1)
