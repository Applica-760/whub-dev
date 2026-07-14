"""Shared error and diagnostic types for wflow services."""
from __future__ import annotations

from dataclasses import dataclass


class WflowError(Exception):
    """Raised when a wflow YAML file cannot be loaded or validated."""


@dataclass(frozen=True)
class Diagnostic:
    """A semantic error in a wflow document."""

    code: str
    message: str
