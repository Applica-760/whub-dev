"""Release command tests."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from whub.cli import main
from whub.commands.release import release
from whub.services.release import ReleaseBuild


def test_build_requires_source() -> None:
    result = CliRunner().invoke(main, ["release", "build"])

    assert result.exit_code == 2
    assert "Missing option '--source'" in result.output


def test_build_reports_staged_wheel(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    wheel = tmp_path / "whub-0.1.0-py3-none-any.whl"
    monkeypatch.setattr(
        "whub.commands.release.build_release",
        lambda value: ReleaseBuild("0.1.0+g12345678", wheel),
    )

    result = CliRunner().invoke(
        release,
        ["build", "--source", str(source)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert result.output == f"built 0.1.0+g12345678: {wheel}\n"
