"""Inbox service behavior tests.

検証するケース:
1. 日時付きファイル名で投函し、本文を無加工で書き込む。
2. 空title・空body・ファイル名に使えない文字を拒否する。
3. 同名ファイルの上書きを拒否する。
4. vault projectの未定義・未linkを拒否する。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from whub.models import Manifest
from whub.services.errors import ServiceError
from whub.services.inbox import create_inbox_note
from whub.tests.helpers import manifest, manifest_data


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None) -> FrozenDatetime:
        return cls(2026, 7, 10, 16, 30, tzinfo=tz)


def _vault_manifest(tmp_path: Path) -> tuple[Manifest, Path]:
    source = tmp_path / "vault-source"
    source.mkdir()
    (source / "inbox").mkdir()
    data = manifest_data()
    data["projects"].append({
        "name": "vault",
        "resource": {
            "type": "symlink",
            "workspace_path": "vault",
            "source": str(source),
        },
    })
    result = Manifest.model_validate(data)
    project = result.resolve_project("vault")
    assert project is not None
    assert project.resource is not None
    workspace_path = tmp_path / "vault"
    workspace_path.symlink_to(source, target_is_directory=True)
    project.resource._resolved_workspace_path = workspace_path
    return result, workspace_path


def test_create_inbox_note_writes_unmodified_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("whub.services.inbox.datetime", FrozenDatetime)
    vault_manifest, vault_path = _vault_manifest(tmp_path)

    path = create_inbox_note(vault_manifest, "  first note  ", "  raw body\n")

    assert path == vault_path / "inbox" / "20260710_1630_first note.md"
    assert path.read_text() == "  raw body\n"


@pytest.mark.parametrize(
    "title",
    [
        " ",
        "bad/name",
        "bad\\name",
        "bad:name",
        "bad*name",
        "bad?name",
        'bad"name',
        "bad<name",
        "bad>name",
        "bad|name",
        "bad\tname",
        "bad\x7fname",
    ],
)
def test_create_inbox_note_rejects_invalid_title(tmp_path: Path, title: str) -> None:
    vault_manifest, _ = _vault_manifest(tmp_path)

    with pytest.raises(ServiceError):
        create_inbox_note(vault_manifest, title, "body")


def test_create_inbox_note_rejects_empty_body(tmp_path: Path) -> None:
    vault_manifest, _ = _vault_manifest(tmp_path)

    with pytest.raises(ServiceError, match="body is required"):
        create_inbox_note(vault_manifest, "note", " \n")


def test_create_inbox_note_rejects_name_collision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("whub.services.inbox.datetime", FrozenDatetime)
    vault_manifest, _ = _vault_manifest(tmp_path)
    create_inbox_note(vault_manifest, "note", "first")

    with pytest.raises(ServiceError, match="already exists"):
        create_inbox_note(vault_manifest, "note", "second")


def test_create_inbox_note_rejects_missing_vault_project() -> None:
    with pytest.raises(ServiceError, match="vault project is not defined"):
        create_inbox_note(manifest(), "note", "body")


def test_create_inbox_note_rejects_unlinked_vault(tmp_path: Path) -> None:
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    vault_path.unlink()

    with pytest.raises(ServiceError, match="vault workspace path is not available"):
        create_inbox_note(vault_manifest, "note", "body")
