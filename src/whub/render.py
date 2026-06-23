"""Rendering helpers for CLI output."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence


def render_table(
    rows: Sequence[Sequence[object]],
    *,
    right_align: set[int] | None = None,
    padding: str = "  ",
) -> list[str]:
    """Render rows as a display-width-aware table."""
    if not rows:
        return []

    def display_width(value: object) -> int:
        width = 0
        for char in str(value):
            if unicodedata.combining(char):
                continue
            width += 2 if unicodedata.east_asian_width(char) in ("F", "W") else 1
        return width

    def pad(value: object, width: int, *, right: bool) -> str:
        text = str(value)
        spaces = " " * max(width - display_width(text), 0)
        return spaces + text if right else text + spaces

    column_count = max(len(row) for row in rows)
    widths = [
        max(display_width(row[index]) if index < len(row) else 0 for row in rows)
        for index in range(column_count)
    ]
    right_aligned = right_align or set()

    lines: list[str] = []
    for row in rows:
        columns = []
        for index, width in enumerate(widths):
            value = row[index] if index < len(row) else ""
            columns.append(pad(value, width, right=index in right_aligned))
        lines.append(padding.join(columns).rstrip())
    return lines
