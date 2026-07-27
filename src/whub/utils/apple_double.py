"""AppleDouble path helpers."""

from __future__ import annotations

from pathlib import Path

APPLE_DOUBLE_PREFIX = "._"
APPLE_DOUBLE_MAGIC = b"\x00\x05\x16\x07"


def is_apple_double(path: Path) -> bool:
    """Return whether PATH is an AppleDouble sidecar."""
    return path.name.startswith(APPLE_DOUBLE_PREFIX)
