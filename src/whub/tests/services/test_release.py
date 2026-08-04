"""Operation release build tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from whub.core.context import WhubContext
from whub.services.release import (
    ReleaseBuildError,
    ReleaseApplyError,
    ReleaseVerifyError,
    apply_release,
    build_release,
    verify_release,
)


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
    current_release = context.releases_dir / "0.0.1+g00000000"
    executable = current_release / "venv" / "bin" / "whub"
    executable.parent.mkdir(parents=True)
    executable.touch()
    os.symlink(current_release, context.releases_dir / "current")
    return context


def _result(
    command: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "build failed",
):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _wheel(context: WhubContext, release_id: str, *, valid_webapp: bool = True) -> Path:
    wheel = context.releases_dir / ".staging" / release_id / "artifact" / "whub-0.1.0-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "whub/_build.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "package_version": "0.1.0",
                    "source_commit": "a" * 40,
                }
            ),
        )
        archive.writestr(
            "whub-0.1.0.dist-info/entry_points.txt",
            "[console_scripts]\nwhub = whub.cli:main\nwflow = whub.wflow.cli:main\n",
        )
        if valid_webapp:
            archive.writestr("whub/webapp/dist/index.html", "<html></html>")
            archive.writestr("whub/webapp/dist/assets/app.js", "console.log('ok')")
    return wheel


def _verified_staging(context: WhubContext, release_id: str) -> Path:
    wheel = _wheel(context, release_id)
    staging = wheel.parents[1]
    (staging / "venv" / "bin").mkdir(parents=True)
    (staging / "venv" / "bin" / "whub").touch()
    (staging / "release.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "release_id": release_id,
                "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "verified": True,
            }
        )
    )
    return staging


def test_build_stages_wheel_and_removes_generated_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    context = _context(tmp_path)
    calls: list[list[str]] = []

    def run(command, *, cwd, capture_output, text, env=None):
        del capture_output, text, env
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

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    result = build_release(source, context=context)

    assert result.release_id == "0.1.0+gaaaaaaaa"
    assert result.wheel_path.is_file()
    assert not (source / "src" / "whub" / "_build.json").exists()
    assert calls[2] == [sys.executable, "-m", "whub", "app", "down"]
    assert ["npm", "run", "build"] in calls


def test_build_failure_restarts_operation_app(monkeypatch, tmp_path: Path) -> None:
    source = _source(tmp_path)
    context = _context(tmp_path)
    calls: list[list[str]] = []

    def run(command, *, cwd, capture_output, text, env=None):
        del cwd, capture_output, text, env
        calls.append(command)
        if command[:3] == ["git", "status", "--porcelain"]:
            return _result(command)
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return _result(command, stdout="a" * 40 + "\n")
        if command == ["npm", "run", "build"]:
            return _result(command, returncode=1)
        return _result(command)

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    with pytest.raises(ReleaseBuildError, match="npm run build"):
        build_release(source, context=context)

    assert calls[-1][-1] == "app"
    assert not (source / "src" / "whub" / "_build.json").exists()


def test_build_recovers_rollup_native_dependency_once(monkeypatch, tmp_path: Path) -> None:
    source = _source(tmp_path)
    context = _context(tmp_path)
    calls: list[list[str]] = []
    build_attempts = 0

    def run(command, *, cwd, capture_output, text, env=None):
        del cwd, capture_output, text, env
        nonlocal build_attempts
        calls.append(command)
        if command[:3] == ["git", "status", "--porcelain"]:
            return _result(command)
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return _result(command, stdout="a" * 40 + "\n")
        if command == ["npm", "run", "build"]:
            build_attempts += 1
            if build_attempts == 1:
                return _result(
                    command,
                    returncode=1,
                    stderr="Cannot find module '@rollup/rollup-darwin-arm64'",
                )
        if command[:3] == ["uv", "build", "--wheel"]:
            output = Path(command[command.index("--out-dir") + 1])
            output.mkdir(parents=True, exist_ok=True)
            (output / "whub-0.1.0-py3-none-any.whl").touch()
        return _result(command)

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    result = build_release(source, context=context)

    assert result.wheel_path.is_file()
    assert calls.count(["npm", "run", "build"]) == 2
    assert ["npm", "ci"] in calls


def test_verify_records_wheel_hash_after_staging_smoke_test(monkeypatch, tmp_path: Path) -> None:
    context = _context(tmp_path)
    release_id = "0.1.0+gaaaaaaaa"
    wheel = _wheel(context, release_id)
    calls: list[list[str]] = []

    def run(command, *, cwd, capture_output, text, env=None):
        del cwd, capture_output, text, env
        calls.append(command)
        if command[:3] == ["uv", "venv", "--clear"]:
            venv = Path(command[-1])
            (venv / "bin").mkdir(parents=True)
            for executable in ("python", "whub", "wflow"):
                (venv / "bin" / executable).touch()
        if command[-1] == "--version":
            return _result(command, stdout="whub, version 0.1.0 (commit " + "a" * 40 + ")\n")
        return _result(command)

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    result = verify_release(release_id, context=context)

    expected_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
    release_json = wheel.parents[1] / "release.json"
    assert result.wheel_sha256 == expected_hash
    assert json.loads(release_json.read_text()) == {
        "schema_version": 1,
        "release_id": release_id,
        "wheel_sha256": expected_hash,
        "verified": True,
    }
    assert [str(wheel.parents[1] / "venv" / "bin" / "wflow"), "--help"] in calls


def test_verify_isolates_staging_venv_from_caller_interpreter_vars(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """検証はwheel由来の実装だけを見る。呼び出し側のPYTHONPATHを継承しない。"""
    context = _context(tmp_path)
    release_id = "0.1.0+gaaaaaaaa"
    _wheel(context, release_id)
    monkeypatch.setenv("PYTHONPATH", "/checkout/src")
    monkeypatch.setenv("VIRTUAL_ENV", "/other/venv")
    envs: list[dict[str, str] | None] = []

    def run(command, *, cwd, capture_output, text, env=None):
        del cwd, capture_output, text
        envs.append(env)
        if command[:3] == ["uv", "venv", "--clear"]:
            venv = Path(command[-1])
            (venv / "bin").mkdir(parents=True)
            for executable in ("python", "whub", "wflow"):
                (venv / "bin" / executable).touch()
        if command[-1] == "--version":
            return _result(command, stdout="whub, version 0.1.0 (commit " + "a" * 40 + ")\n")
        return _result(command)

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    verify_release(release_id, context=context)

    assert envs and all(env is not None for env in envs)
    for env in envs:
        assert "PYTHONPATH" not in env
        assert "VIRTUAL_ENV" not in env
        # 遮断するのは解釈系の上書きだけで、他の環境変数は保つ
        assert env["PATH"] == os.environ["PATH"]


def test_verify_failure_restarts_operation_app(monkeypatch, tmp_path: Path) -> None:
    context = _context(tmp_path)
    release_id = "0.1.0+gaaaaaaaa"
    _wheel(context, release_id, valid_webapp=False)
    calls: list[list[str]] = []

    def run(command, *, cwd, capture_output, text, env=None):
        del cwd, capture_output, text, env
        calls.append(command)
        return _result(command)

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    with pytest.raises(ReleaseVerifyError, match="webapp index.html"):
        verify_release(release_id, context=context)

    assert calls[-1][-1] == "app"


def test_apply_moves_verified_release_and_switches_current(monkeypatch, tmp_path: Path) -> None:
    context = _context(tmp_path)
    release_id = "0.1.0+gaaaaaaaa"
    staging = _verified_staging(context, release_id)
    calls: list[list[str]] = []
    envs: list[dict[str, str] | None] = []
    monkeypatch.setenv("PYTHONPATH", "/checkout/src")
    monkeypatch.setenv("VIRTUAL_ENV", "/other/venv")

    def run(command, *, cwd, capture_output, text, env=None):
        del cwd, capture_output, text
        calls.append(command)
        envs.append(env)
        return _result(command)

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    result = apply_release(release_id, context=context)

    assert result.release_path == context.releases_dir / release_id
    assert not staging.exists()
    assert (context.releases_dir / "current").resolve() == result.release_path
    assert calls == [
        ["uv", "venv", "--clear", "--no-project", str(result.release_path / "venv")],
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(result.release_path / "venv" / "bin" / "python"),
            str(result.release_path / "artifact" / "whub-0.1.0-py3-none-any.whl"),
        ],
        [str(result.release_path / "venv" / "bin" / "whub"), "--version"],
        [str(result.release_path / "venv" / "bin" / "whub"), "app"],
    ]
    assert envs and all(env is not None for env in envs)
    for env in envs:
        assert "PYTHONPATH" not in env
        assert "VIRTUAL_ENV" not in env


def test_apply_failure_restores_current_and_staging(monkeypatch, tmp_path: Path) -> None:
    context = _context(tmp_path)
    release_id = "0.1.0+gaaaaaaaa"
    staging = _verified_staging(context, release_id)
    old_release = (context.releases_dir / "current").resolve()
    calls: list[list[str]] = []

    def run(command, *, cwd, capture_output, text, env=None):
        del cwd, capture_output, text, env
        calls.append(command)
        if command == [
            str(context.releases_dir / release_id / "venv" / "bin" / "whub"),
            "app",
        ]:
            return _result(command, returncode=1)
        return _result(command)

    monkeypatch.setattr("whub.services.release.shared.subprocess.run", run)

    with pytest.raises(ReleaseApplyError, match="app"):
        apply_release(release_id, context=context)

    assert staging.is_dir()
    assert (context.releases_dir / "current").resolve() == old_release
    assert calls[-1] == [str(context.releases_dir / "current" / "venv" / "bin" / "whub"), "app"]
