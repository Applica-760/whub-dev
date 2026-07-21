"""Models for Project-local remote GUI session descriptors."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


SessionState = Literal["pending", "running", "completed", "failed", "interrupted"]
RunId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]


class SessionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionPane(SessionModel):
    pane_id: str
    window_id: str
    window_name: str
    pane_index: int
    transcript: str = Field(
        pattern=r"^\.whub/runs/[A-Za-z0-9][A-Za-z0-9._-]*/panes/[A-Za-z0-9._-]+\.log$"
    )
    dead: bool = False
    dead_status: int | None = None
    dead_signal: int | None = None


class SessionTmux(SessionModel):
    socket: str
    session: str


class SessionDescriptor(SessionModel):
    schema_version: Literal[1] = 1
    protocol_version: Literal[1] = 1
    project: str = Field(min_length=1)
    task: str | None = Field(default=None, pattern=r"^TASK-[0-9]+$")
    run_id: RunId
    state: SessionState
    created_at: datetime
    updated_at: datetime
    tmux: SessionTmux | None = None
    panes: list[SessionPane] = Field(default_factory=list)
