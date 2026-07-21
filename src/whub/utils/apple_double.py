"""AppleDouble path helpers."""

from __future__ import annotations

from pathlib import Path


def is_apple_double(path: Path) -> bool:
    """Return whether PATH is an AppleDouble sidecar."""
    return path.name.startswith("._")
