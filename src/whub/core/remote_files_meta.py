"""Metadata for files fetched into the remote_files directory."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

_META_FILENAME = ".whub-meta.json"


@dataclass(frozen=True)
class RemoteFileRecord:
    ref: str
    sha256: str
    fetched_at: str


def meta_path(remote_files_dir: Path) -> Path:
    return remote_files_dir / _META_FILENAME


def load_remote_files_meta(remote_files_dir: Path) -> dict[str, RemoteFileRecord]:
    path = meta_path(remote_files_dir)
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {
        name: RemoteFileRecord(
            ref=entry["ref"],
            sha256=entry["sha256"],
            fetched_at=entry["fetched_at"],
        )
        for name, entry in data.items()
    }


def get_remote_file_record(
    remote_files_dir: Path, local_name: str
) -> RemoteFileRecord | None:
    return load_remote_files_meta(remote_files_dir).get(local_name)


def resolve_remote_file_name(
    remote_files_dir: Path, ref: str, preferred_name: str
) -> str:
    """同一refの既存remote fileは同名を再利用し、新規はbasename衝突を連番で回避する。"""
    records = load_remote_files_meta(remote_files_dir)
    for name, record in records.items():
        if record.ref == ref:
            return name

    stem = Path(preferred_name).stem
    suffix = Path(preferred_name).suffix
    candidate = preferred_name
    index = 2
    while candidate in records or (remote_files_dir / candidate).exists():
        candidate = f"{stem}-{index}{suffix}"
        index += 1
    return candidate


def record_remote_file(
    remote_files_dir: Path,
    local_name: str,
    ref: str,
    sha256: str,
    fetched_at: str,
) -> None:
    records = load_remote_files_meta(remote_files_dir)
    records[local_name] = RemoteFileRecord(ref=ref, sha256=sha256, fetched_at=fetched_at)
    _write(remote_files_dir, records)


def update_remote_file_hash(
    remote_files_dir: Path, local_name: str, sha256: str, pushed_at: str
) -> None:
    records = load_remote_files_meta(remote_files_dir)
    existing = records[local_name]
    records[local_name] = RemoteFileRecord(
        ref=existing.ref, sha256=sha256, fetched_at=pushed_at
    )
    _write(remote_files_dir, records)


def remove_remote_file_record(remote_files_dir: Path, local_name: str) -> None:
    records = load_remote_files_meta(remote_files_dir)
    del records[local_name]
    _write(remote_files_dir, records)


def _write(remote_files_dir: Path, records: dict[str, RemoteFileRecord]) -> None:
    if not records:
        meta_path(remote_files_dir).unlink(missing_ok=True)
        return
    remote_files_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        name: {
            "ref": record.ref,
            "sha256": record.sha256,
            "fetched_at": record.fetched_at,
        }
        for name, record in records.items()
    }
    meta_path(remote_files_dir).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
