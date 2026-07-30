"""Whub wheel Web app distribution integration test."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import zipfile


PROJECT_ROOT = Path(__file__).parents[4]


def test_wheel_serves_packaged_app_from_operation_context(tmp_path: Path) -> None:
    built_index = PROJECT_ROOT / "src" / "whub" / "webapp" / "dist" / "index.html"
    assert built_index.is_file(), "run `cd app && npm run build` before Python tests"

    wheel_dir = tmp_path / "wheel"
    build = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    wheel = next(wheel_dir.glob("whub-*.whl"))

    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    assert "whub/webapp/dist/index.html" in names
    assert any(name.startswith("whub/webapp/dist/assets/") for name in names)
    assert "whub/assets/cleanup/appledouble.py" in names
    assert not any(name.startswith("app/") for name in names)

    installed = tmp_path / "installed"
    install = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--target",
            str(installed),
            "--no-deps",
            str(wheel),
        ],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stderr

    context_root = tmp_path / "operation"
    context_root.mkdir()
    fake_home = tmp_path / "home"
    config_dir = fake_home / ".whub"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(f'workspace_root = "{context_root}"\n')
    probe = subprocess.run(
        [sys.executable, "-c", _INSTALLED_WHEEL_PROBE, str(installed)],
        cwd=context_root,
        env={
            **os.environ,
            "HOME": str(fake_home),
            "PYTHONPATH": str(installed),
        },
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr


_INSTALLED_WHEEL_PROBE = """
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import whub
from whub.core.context import current_context
from whub.webapp.resources import (
    AppResourceError,
    development_app_source,
    packaged_app_dist,
)
from whub.webapp.server import create_app

installed = Path(sys.argv[1]).resolve()
assert Path(whub.__file__).resolve().is_relative_to(installed)
assert current_context().directory == Path.home() / ".whub"
assert current_context().workspace_root == Path.cwd()
dist_dir = packaged_app_dist()
assert dist_dir.is_relative_to(installed)
client = TestClient(create_app(dist_dir))
assert client.get("/").status_code == 200
assert client.get("/api/health").json() == {"status": "ok"}
try:
    development_app_source()
except AppResourceError:
    pass
else:
    raise AssertionError("installed wheel resolved development app source")
"""
