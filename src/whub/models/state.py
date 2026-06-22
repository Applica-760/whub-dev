"""Mutable resource state (status text, priority) stored in .whub/state.yaml."""

from __future__ import annotations
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel

STATE_PATH = Path(".whub/state.yaml")

PRIORITY_EMOJI: dict[str | None, str] = {
    "red": "🔴",
    "yellow": "🟡",
    "blue": "🔵",
    "none": "─",
    None: "─",
}

class ResourceState(BaseModel):
    status: str | None = None
    priority: Literal["red", "yellow", "blue", "none"] | None = None

    @property
    def priority_icon(self) -> str:
        return PRIORITY_EMOJI[self.priority]

class State(BaseModel):
    resources: dict[str, ResourceState] = {}

def load_state() -> State:
    if not STATE_PATH.exists():
        return State()
    data = yaml.safe_load(STATE_PATH.read_text())
    if not data:
        return State()
    return State.model_validate(data)

def save_state(state: State) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        yaml.dump(state.model_dump(exclude_none=True), allow_unicode=True, default_flow_style=False),
    )
