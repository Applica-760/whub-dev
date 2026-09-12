"""Models for Agent terminal bridge access."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from whub.models.operator_terminal import OperatorTerminalRef


class TerminalBridgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TerminalAccessMode(StrEnum):
    VIEWER = "viewer"
    CONTROLLER = "controller"


class TerminalSessionRef(TerminalBridgeModel):
    project: str = Field(min_length=1)
    issue_number: int = Field(ge=1)


class TerminalLease(TerminalBridgeModel):
    session: TerminalSessionRef | OperatorTerminalRef
    connection_id: str = Field(min_length=1)
    mode: TerminalAccessMode


class TerminalClaim(TerminalBridgeModel):
    type: Literal["claim"]


class TerminalRelease(TerminalBridgeModel):
    type: Literal["release"]


class TerminalInput(TerminalBridgeModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    type: Literal["input"]
    data: str


class TerminalResize(TerminalBridgeModel):
    type: Literal["resize"]
    columns: int = Field(ge=1, le=1000)
    rows: int = Field(ge=1, le=1000)
