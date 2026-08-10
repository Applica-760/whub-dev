"""Read-only workspace status models."""

from __future__ import annotations

from dataclasses import dataclass

from typing import Literal

HealthState = Literal[
    "ok",
    "missing",
    "source-missing",
    "broken",
    "wrong-target",
    "unexpected",
    "unreachable",
    "unmounted",
    "stale",
    "unreadable",
    "slow",
]


@dataclass(frozen=True)
class ResourceStatus:
    """One workspace resource and its health."""

    project: str
    state: HealthState
    type: str
    mount: str = "-"
    tmux: str = "-"
    git: str = "-"
