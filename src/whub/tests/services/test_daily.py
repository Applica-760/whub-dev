"""Daily entry service behavior tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from whub.models import Manifest
from whub.services.daily import append_daily_entry
from whub.services.errors import ServiceError
from whub.services.manifest import resolve_manifest
from whub.tests.helpers import manifest, manifest_data


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None) -> FrozenDatetime:
        return cls(2026, 7, 28, 16, 30, tzinfo=tz)


class NextDayDatetime(datetime):
    @classmethod
    def now(cls, tz=None) -> NextDayDatetime:
        return cls(2026, 7, 29, 0, 5, tzinfo=tz)


def _vault_manifest(tmp_path: Path) -> tuple[Manifest, Path]:
    source = tmp_path / "vault-source"
    (source / "daily").mkdir(parents=True)
    data = manifest_data()
    data["projects"].append(
        {
            "name": "vault",
            "resource": {
                "type": "symlink",
                "workspace_path": "vault",
                "source": str(source),
            },
        }
    )
    result = resolve_manifest(Manifest.model_validate(data), tmp_path)
    project = result.resolve_project("vault")
    assert project is not None
    assert project.resource is not None
    workspace_path = tmp_path / "vault"
    workspace_path.symlink_to(source, target_is_directory=True)
    project.resource.workspace_path = str(workspace_path)
    return result, workspace_path


def test_append_daily_entry_creates_daily_with_unmodified_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("whub.services.daily.datetime", FrozenDatetime)
    vault_manifest, vault_path = _vault_manifest(tmp_path)

    path = append_daily_entry(vault_manifest, "  raw body\n")

    assert path == vault_path / "daily" / "2026-07-28.md"
    assert path.read_text() == (
        "---\n"
        "tags:\n"
        "  - Daily\n"
        "---\n"
        "\n"
        "## 16:30\n"
        "\n"
        "  raw body\n"
    )


def test_append_daily_entry_appends_existing_daily_in_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("whub.services.daily.datetime", FrozenDatetime)
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    path = vault_path / "daily" / "2026-07-28.md"
    path.write_text("# existing\n", encoding="utf-8")

    append_daily_entry(vault_manifest, "body", energy=4)

    assert path.read_text() == (
        "# existing\n"
        "\n"
        "## 16:30\n"
        "\n"
        "元気度: 4/5\n"
        "\n"
        "body"
    )


def test_append_daily_entry_keeps_same_day_posts_in_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("whub.services.daily.datetime", FrozenDatetime)
    vault_manifest, vault_path = _vault_manifest(tmp_path)

    append_daily_entry(vault_manifest, "first")
    append_daily_entry(vault_manifest, "second")

    content = (vault_path / "daily" / "2026-07-28.md").read_text()
    assert content.index("first") < content.index("second")
    assert content.count("## 16:30") == 2


def test_append_daily_entry_uses_a_new_file_after_date_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    monkeypatch.setattr("whub.services.daily.datetime", FrozenDatetime)
    append_daily_entry(vault_manifest, "yesterday")
    monkeypatch.setattr("whub.services.daily.datetime", NextDayDatetime)

    path = append_daily_entry(vault_manifest, "today")

    assert path == vault_path / "daily" / "2026-07-29.md"
    assert "today" in path.read_text()
    assert "today" not in (vault_path / "daily" / "2026-07-28.md").read_text()


@pytest.mark.parametrize("energy", [0, 6, True])
def test_append_daily_entry_rejects_invalid_energy(
    tmp_path: Path,
    energy: int,
) -> None:
    vault_manifest, _ = _vault_manifest(tmp_path)

    with pytest.raises(ServiceError, match="energy must be between 1 and 5"):
        append_daily_entry(vault_manifest, "body", energy=energy)


def test_append_daily_entry_rejects_blank_body(tmp_path: Path) -> None:
    vault_manifest, _ = _vault_manifest(tmp_path)

    with pytest.raises(ServiceError, match="daily body is required"):
        append_daily_entry(vault_manifest, " \n")


def test_append_daily_entry_rejects_missing_vault_project() -> None:
    with pytest.raises(ServiceError, match="vault project is not defined"):
        append_daily_entry(manifest(), "body")


def test_append_daily_entry_rejects_unavailable_vault(tmp_path: Path) -> None:
    vault_manifest, vault_path = _vault_manifest(tmp_path)
    vault_path.unlink()

    with pytest.raises(ServiceError, match="vault workspace path is not available"):
        append_daily_entry(vault_manifest, "body")
