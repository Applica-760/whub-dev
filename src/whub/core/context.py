"""Whub operation context and managed-file access."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
import tomllib


class PathError(Exception):
    """Raised when a Whub context path cannot be resolved."""


DEFAULT_CONTEXT_DIR = Path.home() / ".whub"


@dataclass(frozen=True)
class WhubContext:
    """Access Whub-owned files without exposing their storage layout."""

    directory: Path

    @property
    def workspace_root(self) -> Path:
        try:
            config = tomllib.loads(self.config_path.read_text())
        except FileNotFoundError as error:
            raise PathError(f"whub config not found: {self.config_path}") from error
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
            raise PathError(
                f"invalid whub config: {self.config_path}: {error}"
            ) from error

        value = config.get("workspace_root")
        if not isinstance(value, str) or not value.strip():
            raise PathError(
                f"invalid whub config: {self.config_path}: "
                "workspace_root must be a non-empty absolute path"
            )
        root = Path(value).expanduser()
        if not root.is_absolute():
            raise PathError(
                f"invalid whub config: {self.config_path}: "
                "workspace_root must be a non-empty absolute path"
            )
        if not root.is_dir():
            raise PathError(f"workspace root does not exist: {root}")
        return root

    @property
    def config_path(self) -> Path:
        return self.directory / "config.toml"

    @property
    def manifest_path(self) -> Path:
        return self.directory / "manifest.yaml"

    @property
    def todo_path(self) -> Path:
        return self.directory / "todos.yaml"

    @property
    def remote_files_dir(self) -> Path:
        return self.workspace_root / "remote_files"

    @property
    def releases_dir(self) -> Path:
        return self.directory / "releases"

    @property
    def app_pid_path(self) -> Path:
        return self.directory / "app.pid"

    @property
    def app_dev_pid_path(self) -> Path:
        return self.directory / "app-dev.pid"

    @property
    def operator_terminal_path(self) -> Path:
        return self.directory / "runtime" / "operator-terminal.json"

    @property
    def operator_terminals_path(self) -> Path:
        return self.directory / "runtime" / "operator-terminals.json"

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
    """Return the fixed user operation context."""
    return WhubContext(DEFAULT_CONTEXT_DIR)


def reset_context() -> None:
    """Forget the cached context for an isolated invocation or test."""
    current_context.cache_clear()
