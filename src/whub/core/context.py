"""Whub operation context and managed-file access."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import cache, cached_property
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
        """Resolve the Phase 1 context while preserving legacy overrides."""
        override = os.environ.get("WHUB_ROOT")
        if override:
            return cls(Path(override).expanduser().resolve())
        try:
            return cls(find_context_root(invocation_path()))
        except PathError:
            return cls(_package_workspace_root())

    @property
    def config_dir(self) -> Path:
        return self.root / ".whub"

    @property
    def config_path(self) -> Path:
        return self.config_dir / "config.toml"

    @cached_property
    def _legacy_data_dir(self) -> Path:
        override = os.environ.get("WHUB_DATA_DIR")
        if override:
            return Path(override).expanduser().resolve()

        if not self.config_path.exists():
            raise PathError(
                "whub data_dir is not configured; run `whub init <data_dir>` "
                f"to create {self.config_path}"
            )
        try:
            data = tomllib.loads(self.config_path.read_text())
        except tomllib.TOMLDecodeError as error:
            raise PathError(
                f"invalid whub config: {self.config_path}: {error}"
            ) from error

        value = data.get("data_dir")
        if not isinstance(value, str) or not value:
            raise PathError(f"whub config missing data_dir: {self.config_path}")
        return Path(value).expanduser().resolve()

    @property
    def manifest_path(self) -> Path:
        return self._legacy_data_dir / "manifest.yaml"

    @property
    def todo_path(self) -> Path:
        return self._legacy_data_dir / "todos.yaml"

    @property
    def downloads_dir(self) -> Path:
        return self._legacy_data_dir / "downloads"

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


def _package_workspace_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "whub").exists():
            return parent
    return current.parents[2]
