"""Rendering helpers for CLI output."""
from __future__ import annotations
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
import click

@dataclass(frozen=True)
class TableCell:
    value: object
    fg: str | None = None
    bold: bool = False


def render_table(
    rows: Sequence[Sequence[object]],
    *,
    headers: Sequence[object] | None = None,
    right_align: set[int] | None = None,
) -> None:
    table_rows = ([headers] if headers is not None else []) + list(rows)
    if not table_rows:
        return

    def cell_value(cell: object) -> object:
        return cell.value if isinstance(cell, TableCell) else cell

    def display_width(value: object) -> int:
        width = 0
        for char in str(value):
            if unicodedata.combining(char):
                continue
            width += 2 if unicodedata.east_asian_width(char) in ("F", "W") else 1
        return width

    def pad(value: object, width: int, *, right: bool) -> str:
        text = str(cell_value(value))
        spaces = " " * max(width - display_width(text), 0)
        return spaces + text if right else text + spaces

    def decorate_cell(cell: object, text: str, *, header: bool) -> str:
        if isinstance(cell, TableCell):
            return click.style(text, fg=cell.fg, bold=header or cell.bold)
        if header:
            return click.style(text, bold=True)
        return text

    column_count = max(len(row) for row in table_rows)
    widths = [
        max(
            display_width(cell_value(row[index])) if index < len(row) else 0
            for row in table_rows
        )
        for index in range(column_count)
    ]
    right_aligned = right_align or set()

    click.echo()
    for row_index, row in enumerate(table_rows):
        columns = []
        is_header = headers is not None and row_index == 0
        for index, width in enumerate(widths):
            value = row[index] if index < len(row) else ""
            text = pad(
                value,
                width,
                right=not is_header and index in right_aligned,
            )
            columns.append(decorate_cell(value, text, header=is_header))
        click.echo(f"  {'  '.join(columns).rstrip()}")
        if is_header:
            separator_width = sum(widths) + 2 * (len(widths) - 1)
            click.echo(f"  {'-' * separator_width}")
    click.echo()
