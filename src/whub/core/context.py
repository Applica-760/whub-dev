"""Whub operation context and managed-file access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path


class PathError(Exception):
    """Raised when a Whub context path cannot be resolved."""


def find_context_root(start: Path) -> Path:
    """Find the nearest Whub context at or above START."""
    expanded_start = start.expanduser()
    absolute_start = (
        expanded_start if expanded_start.is_absolute() else Path.cwd() / expanded_start
    )
    for candidate in (absolute_start, *absolute_start.parents):
        if (candidate / ".whub" / "config.toml").is_file():
            return candidate
    raise PathError(
        f"whub context not found from {absolute_start}: "
        "expected .whub/config.toml in the current directory or an ancestor"
    )


def invocation_path() -> Path:
    """Return a verified logical invocation path when available."""
    physical = Path.cwd()
    value = os.environ.get("PWD")
    if not value:
        return physical

    logical = Path(value).expanduser()
    if not logical.is_absolute():
        return physical
    try:
        if logical.samefile(physical):
            return logical
    except OSError:
        pass
    return physical


@dataclass(frozen=True)
class WhubContext:
    """Access Whub-owned files without exposing their storage layout."""

    root: Path

    @classmethod
    def discover(cls) -> WhubContext:
        """Resolve the nearest context from the verified invocation path."""
        return cls(find_context_root(invocation_path()))

    @property
    def config_dir(self) -> Path:
        return self.root / ".whub"

    @property
    def config_path(self) -> Path:
        return self.config_dir / "config.toml"

    @property
    def manifest_path(self) -> Path:
        return self.config_dir / "manifest.yaml"

    @property
    def todo_path(self) -> Path:
        return self.config_dir / "todos.yaml"

    @property
    def downloads_dir(self) -> Path:
        return self.config_dir / "downloads"

    @property
    def app_dist_path(self) -> Path:
        return self.root / "app" / "dist"

    @property
    def app_pid_path(self) -> Path:
        return self.config_dir / "app.pid"

    @property
    def app_dev_pid_path(self) -> Path:
        return self.config_dir / "app-dev.pid"

    def read_manifest_text(self) -> str:
        return self.manifest_path.read_text()

    def read_todo_text(self) -> str | None:
        if not self.todo_path.exists():
            return None
        return self.todo_path.read_text()

    def write_todo_text(self, content: str) -> None:
        self.todo_path.parent.mkdir(parents=True, exist_ok=True)
        self.todo_path.write_text(content)


@cache
def current_context() -> WhubContext:
    """Return the process-wide operation context."""
    return WhubContext.discover()


def reset_context() -> None:
    """Forget the cached context for an isolated invocation or test."""
    current_context.cache_clear()
