"""Shared Flow errors and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


class FlowError(Exception):
    """Raised when a Flow document cannot be loaded or validated."""


@dataclass(frozen=True)
class Diagnostic:
    """A semantic error in a Flow document."""

    code: str
    message: str
