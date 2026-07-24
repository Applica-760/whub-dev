"""Operation release build tests."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from whub.core.context import WhubContext
from whub.services.release import ReleaseBuildError, build_release


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "app").mkdir(parents=True)
    (source / "src" / "whub").mkdir(parents=True)
    (source / "pyproject.toml").write_text(
        "[project]\nname = \"whub\"\nversion = \"0.1.0\"\n"
    )
    return source


def _context(tmp_path: Path) -> WhubContext:
    context = WhubContext(tmp_path / "operation")
    executable = context.releases_dir / "current" / "venv" / "bin" / "whub"
    executable.parent.mkdir(parents=True)
    executable.touch()
    return context


def _result(command: list[str], returncode: int = 0, stdout: str = ""):
    return subprocess.CompletedProcess(command, returncode, stdout, "build failed")


def test_build_stages_wheel_and_removes_generated_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    context = _context(tmp_path)
    calls: list[list[str]] = []

    def run(command, *, cwd, capture_output, text):
        del capture_output, text
        calls.append(command)
        if command[:3] == ["git", "status", "--porcelain"]:
            return _result(command)
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return _result(command, stdout="a" * 40 + "\n")
        if command[:3] == ["uv", "build", "--wheel"]:
            output = Path(command[command.index("--out-dir") + 1])
            output.mkdir(parents=True, exist_ok=True)
            (output / "whub-0.1.0-py3-none-any.whl").touch()
        return _result(command)

    monkeypatch.setattr("whub.services.release.subprocess.run", run)

    result = build_release(source, context=context)

    assert result.release_id == "0.1.0+gaaaaaaaa"
    assert result.wheel_path.is_file()
    assert not (source / "src" / "whub" / "_build.json").exists()
    assert calls[2][-2:] == ["app", "down"]
    assert ["npm", "run", "build"] in calls


def test_build_failure_restarts_operation_app(monkeypatch, tmp_path: Path) -> None:
    source = _source(tmp_path)
    context = _context(tmp_path)
    calls: list[list[str]] = []

    def run(command, *, cwd, capture_output, text):
        del cwd, capture_output, text
        calls.append(command)
        if command[:3] == ["git", "status", "--porcelain"]:
            return _result(command)
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return _result(command, stdout="a" * 40 + "\n")
        if command == ["npm", "run", "build"]:
            return _result(command, returncode=1)
        return _result(command)

    monkeypatch.setattr("whub.services.release.subprocess.run", run)

    with pytest.raises(ReleaseBuildError, match="npm run build"):
        build_release(source, context=context)

    assert calls[-1][-1] == "app"
    assert not (source / "src" / "whub" / "_build.json").exists()
