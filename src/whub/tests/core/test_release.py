"""Packaged Whub release metadata tests."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from whub import release
from whub.cli import main as whub_main
from whub.wflow.cli import main as wflow_main


def test_source_package_has_version_without_commit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release, "package_version", lambda package: "0.1.0")
    monkeypatch.setattr(release, "files", lambda package: tmp_path)

    info = release.current_release()

    assert info.package_version == "0.1.0"
    assert info.source_commit is None
    assert info.release_id == "0.1.0+source"


def test_packaged_release_uses_stamped_commit(monkeypatch, tmp_path: Path) -> None:
    commit = "6ba619ae" + "0" * 32
    (tmp_path / "_build.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "package_version": "0.1.0",
                "source_commit": commit,
            }
        )
    )
    monkeypatch.setattr(release, "package_version", lambda package: "0.1.0")
    monkeypatch.setattr(release, "files", lambda package: tmp_path)

    info = release.current_release()

    assert info.source_commit == commit
    assert info.release_id == "0.1.0+g6ba619ae"
    assert info.display == f"0.1.0 (commit {commit})"


def test_rejects_release_metadata_for_another_version(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "_build.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "package_version": "0.2.0",
                "source_commit": "a" * 40,
            }
        )
    )
    monkeypatch.setattr(release, "package_version", lambda package: "0.1.0")
    monkeypatch.setattr(release, "files", lambda package: tmp_path)

    with pytest.raises(release.ReleaseMetadataError, match="version mismatch"):
        release.current_release()


@pytest.mark.parametrize("commit", ["short", "g" * 40])
def test_rejects_invalid_source_commit(
    monkeypatch,
    tmp_path: Path,
    commit: str,
) -> None:
    (tmp_path / "_build.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "package_version": "0.1.0",
                "source_commit": commit,
            }
        )
    )
    monkeypatch.setattr(release, "package_version", lambda package: "0.1.0")
    monkeypatch.setattr(release, "files", lambda package: tmp_path)

    with pytest.raises(release.ReleaseMetadataError, match="source_commit"):
        release.current_release()


@pytest.mark.parametrize(
    ("command", "program_name"),
    [(whub_main, "whub"), (wflow_main, "wflow")],
)
def test_cli_version_reports_package_and_commit(
    monkeypatch,
    command,
    program_name: str,
) -> None:
    info = release.ReleaseInfo("0.1.0", "a" * 40)
    monkeypatch.setattr(release, "current_release", lambda: info)

    result = CliRunner().invoke(command, ["--version"], catch_exceptions=False)

    assert result.exit_code == 0
    assert result.output == f"{program_name}, version {info.display}\n"
