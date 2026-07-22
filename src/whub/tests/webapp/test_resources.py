"""Web app package and development resource resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from whub.webapp import resources


def test_resolves_packaged_app_dist(monkeypatch, tmp_path: Path) -> None:
    package_root = tmp_path / "whub"
    dist_dir = package_root / "webapp" / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<main>whub</main>")
    monkeypatch.setattr(resources, "files", lambda package: package_root)

    assert resources.packaged_app_dist() == dist_dir


def test_rejects_package_without_built_app(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resources, "files", lambda package: tmp_path / "whub")

    with pytest.raises(resources.AppResourceError, match="distribution is missing"):
        resources.packaged_app_dist()


def test_resolves_development_app_from_checkout(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "src" / "whub" / "webapp" / "resources.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "whub"\n')
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "package.json").write_text("{}")
    monkeypatch.setattr(resources, "__file__", str(source_file))

    assert resources.development_app_source() == app_dir


def test_rejects_installed_package_as_development_checkout(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = (
        tmp_path
        / ".venv"
        / "lib"
        / "python3.12"
        / "site-packages"
        / "whub"
        / "webapp"
        / "resources.py"
    )
    source_file.parent.mkdir(parents=True)
    source_file.write_text("")
    monkeypatch.setattr(resources, "__file__", str(source_file))

    with pytest.raises(resources.AppResourceError, match="checkout is unavailable"):
        resources.development_app_source()
