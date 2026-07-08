"""Helpers for replacing and editing marker-delimited managed blocks."""
from __future__ import annotations

Markers = tuple[str, str]


def format_block(markers: Markers, content: str) -> str:
    body = content.rstrip("\n")
    if body:
        body += "\n"
    return f"{markers[0]}\n{body}{markers[1]}\n"


def managed_range(text: str, markers: Markers) -> tuple[int, int] | None:
    start, end = markers
    if start not in text and end not in text:
        return None
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("duplicate or unpaired managed markers")
    s, e = text.index(start), text.index(end)
    if s > e:
        raise ValueError("start marker appears after end marker")
    e += len(end)
    nl = "\r\n" if text[e : e + 2] == "\r\n" else "\n"
    if text[e : e + len(nl)] == nl:
        e += len(nl)
    return s, e


def replace_or_prepend_block(new: str, existing: str | None, markers: Markers) -> str:
    if managed_range(new, markers) is None:
        raise ValueError("source content missing managed markers")
    if existing is None:
        return new
    rng = managed_range(existing, markers)
    if rng is None:
        return new + "\n" + existing
    return existing[: rng[0]] + new + existing[rng[1] :]


def insert_before_end_marker(content: str, insertion: str, markers: Markers) -> str:
    rng = managed_range(content, markers)
    if rng is None:
        raise ValueError("managed markers are missing")
    end = markers[1]
    _, block_end = rng
    end_index = content.rfind(end, 0, block_end)
    return content[:end_index] + insertion + content[end_index:]
