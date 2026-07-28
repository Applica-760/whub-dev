"""Daily entry storage shared by web adapters."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from whub.models import Manifest
from whub.services.errors import ServiceError
from whub.services.vault import resolve_vault_path


_DAILY_FRONTMATTER = "---\ntags:\n  - Daily\n---\n"


def append_daily_entry(
    manifest: Manifest,
    body: str,
    energy: int | None = None,
) -> Path:
    """Append one timestamped entry to the current local Daily."""
    if not body.strip():
        raise ServiceError("daily body is required")
    if energy is not None and (
        isinstance(energy, bool) or not isinstance(energy, int) or not 1 <= energy <= 5
    ):
        raise ServiceError("energy must be between 1 and 5")

    now = datetime.now()
    path = resolve_vault_path(manifest) / "daily" / f"{now:%Y-%m-%d}.md"
    entry = _format_entry(now, body, energy)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        separator = "\n" if existing.endswith("\n") else "\n\n"
        path.write_text(f"{existing}{separator}{entry}", encoding="utf-8")
    else:
        path.write_text(f"{_DAILY_FRONTMATTER}\n{entry}", encoding="utf-8")
    return path


def _format_entry(now: datetime, body: str, energy: int | None) -> str:
    entry = f"## {now:%H:%M}\n"
    if energy is not None:
        entry += f"\n元気度: {energy}/5\n"
    return f"{entry}\n{body}"
