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
class WorktreeStatus:
    """One registered worktree and its consistency diagnostics."""

    parent_project: str | None
    task_id: str | None
    branch: str | None
    workspace_path: str | None
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResourceStatus:
    """One resource and the worktrees registered below it."""

    project: str
    state: HealthState
    type: str
    mount: str = "-"
    tmux: str = "-"
    git: str = "-"
    worktrees: tuple[WorktreeStatus, ...] = ()


@dataclass(frozen=True)
class StatusReport:
    """Combined resource and worktree health for status adapters."""

    resources: tuple[ResourceStatus, ...]
    invalid_worktrees: tuple[WorktreeStatus, ...] = ()

    @property
    def worktrees(self) -> tuple[WorktreeStatus, ...]:
        return (
            *(item for resource in self.resources for item in resource.worktrees),
            *self.invalid_worktrees,
        )

    @property
    def unhealthy(self) -> bool:
        return any(
            item.state != "ok" or item.mount in {"stale", "unreadable"}
            for item in self.resources
        ) or any(item.diagnostics for item in self.worktrees)
