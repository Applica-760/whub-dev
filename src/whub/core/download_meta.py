"""Metadata for files fetched into the downloads directory."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

_META_FILENAME = ".whub-meta.json"


@dataclass(frozen=True)
class DownloadRecord:
    ref: str
    sha256: str
    fetched_at: str


def meta_path(downloads_dir: Path) -> Path:
    return downloads_dir / _META_FILENAME


def load_download_meta(downloads_dir: Path) -> dict[str, DownloadRecord]:
    path = meta_path(downloads_dir)
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {
        name: DownloadRecord(
            ref=entry["ref"],
            sha256=entry["sha256"],
            fetched_at=entry["fetched_at"],
        )
        for name, entry in data.items()
    }


def get_download_record(downloads_dir: Path, local_name: str) -> DownloadRecord | None:
    return load_download_meta(downloads_dir).get(local_name)


def resolve_local_name(downloads_dir: Path, ref: str, preferred_name: str) -> str:
    """同一refの既存downloadは同名を再利用し、新規はbasename衝突を連番で回避する。"""
    records = load_download_meta(downloads_dir)
    for name, record in records.items():
        if record.ref == ref:
            return name

    stem = Path(preferred_name).stem
    suffix = Path(preferred_name).suffix
    candidate = preferred_name
    index = 2
    while candidate in records or (downloads_dir / candidate).exists():
        candidate = f"{stem}-{index}{suffix}"
        index += 1
    return candidate


def record_download(
    downloads_dir: Path,
    local_name: str,
    ref: str,
    sha256: str,
    fetched_at: str,
) -> None:
    records = load_download_meta(downloads_dir)
    records[local_name] = DownloadRecord(ref=ref, sha256=sha256, fetched_at=fetched_at)
    _write(downloads_dir, records)


def update_download_hash(
    downloads_dir: Path, local_name: str, sha256: str, pushed_at: str
) -> None:
    records = load_download_meta(downloads_dir)
    existing = records[local_name]
    records[local_name] = DownloadRecord(
        ref=existing.ref, sha256=sha256, fetched_at=pushed_at
    )
    _write(downloads_dir, records)


def _write(downloads_dir: Path, records: dict[str, DownloadRecord]) -> None:
    downloads_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        name: {
            "ref": record.ref,
            "sha256": record.sha256,
            "fetched_at": record.fetched_at,
        }
        for name, record in records.items()
    }
    meta_path(downloads_dir).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
