"""Release command tests."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from whub.cli import main
from whub.commands.release import release
from whub.services.release import ReleaseApplication, ReleaseBuild, ReleaseVerification


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


def test_deploy_builds_verifies_and_applies_one_release(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    wheel = tmp_path / "whub-0.1.0-py3-none-any.whl"
    release_path = tmp_path / "releases" / "0.1.0+g12345678"
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        "whub.commands.release.build_release",
        lambda value: calls.append(("build", value))
        or ReleaseBuild("0.1.0+g12345678", wheel),
    )
    monkeypatch.setattr(
        "whub.commands.release.verify_release",
        lambda value: calls.append(("verify", value))
        or ReleaseVerification("0.1.0+g12345678", wheel, "a" * 64),
    )
    monkeypatch.setattr(
        "whub.commands.release.apply_release",
        lambda value: calls.append(("apply", value))
        or ReleaseApplication("0.1.0+g12345678", release_path),
    )

    result = CliRunner().invoke(
        main, ["release", "deploy", "--source", str(source)]
    )

    assert result.exit_code == 0
    assert calls == [
        ("build", source),
        ("verify", "0.1.0+g12345678"),
        ("apply", "0.1.0+g12345678"),
    ]
    assert result.output == f"deployed 0.1.0+g12345678: {release_path}\n"


def test_verify_reports_verified_release(monkeypatch, tmp_path: Path) -> None:
    wheel = tmp_path / "whub-0.1.0-py3-none-any.whl"
    monkeypatch.setattr(
        "whub.commands.release.verify_release",
        lambda value: ReleaseVerification("0.1.0+g12345678", wheel, "a" * 64),
    )

    result = CliRunner().invoke(
        release,
        ["verify", "0.1.0+g12345678"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert result.output == f"verified 0.1.0+g12345678: {'a' * 64}\n"


def test_apply_reports_applied_release(monkeypatch, tmp_path: Path) -> None:
    release_path = tmp_path / "releases" / "0.1.0+g12345678"
    monkeypatch.setattr(
        "whub.commands.release.apply_release",
        lambda value: ReleaseApplication("0.1.0+g12345678", release_path),
    )

    result = CliRunner().invoke(
        release,
        ["apply", "0.1.0+g12345678"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert result.output == f"applied 0.1.0+g12345678: {release_path}\n"
