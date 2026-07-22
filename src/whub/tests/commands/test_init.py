"""Tests for initializing a Whub context."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from whub.commands.init import init


@pytest.fixture()
def invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PWD", str(tmp_path))
    return tmp_path


def test_creates_empty_config_in_current_directory(invocation: Path) -> None:
    result = CliRunner().invoke(init)

    config_path = invocation / ".whub/config.toml"
    assert result.exit_code == 0
    assert "init" in result.output
    assert config_path.is_file()
    assert config_path.read_text() == ""


def test_skips_existing_empty_config(invocation: Path) -> None:
    config_path = invocation / ".whub/config.toml"
    config_path.parent.mkdir()
    config_path.write_text("")

    result = CliRunner().invoke(init)

    assert result.exit_code == 0
    assert "skip" in result.output


def test_rejects_existing_config_without_force(invocation: Path) -> None:
    config_path = invocation / ".whub/config.toml"
    config_path.parent.mkdir()
    config_path.write_text('data_dir = "/legacy"\n')

    result = CliRunner().invoke(init)

    assert result.exit_code != 0
    assert "--force" in result.output
    assert config_path.read_text() == 'data_dir = "/legacy"\n'


def test_overwrites_existing_config_with_force(invocation: Path) -> None:
    config_path = invocation / ".whub/config.toml"
    config_path.parent.mkdir()
    config_path.write_text('data_dir = "/legacy"\n')

    result = CliRunner().invoke(init, ["--force"])

    assert result.exit_code == 0
    assert "init" in result.output
    assert config_path.read_text() == ""


def test_rejects_whub_path_that_is_not_directory(invocation: Path) -> None:
    (invocation / ".whub").write_text("not a directory")

    result = CliRunner().invoke(init)

    assert result.exit_code != 0
    assert "is not a directory" in result.output
