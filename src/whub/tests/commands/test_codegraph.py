from __future__ import annotations

import subprocess
from unittest.mock import patch

from click.testing import CliRunner

from whub.commands.codegraph import codegraph
from whub.models import Manifest
from whub.services.manifest import resolve_manifest
from whub.services.codegraph import initialize_codegraph
from whub.tests.helpers import manifest


def test_local_init_uses_resolved_workspace_path(tmp_path) -> None:
    configured = manifest()
    project = configured.resolve_project("local")
    assert project is not None and project.resource is not None
    project.resource.codegraph = True
    project.resource._resolved_workspace_path = tmp_path / "local"
    project.resource._resolved_workspace_path.mkdir()

    with (
        patch("whub.commands.codegraph.get_manifest", return_value=configured),
        patch("whub.services.codegraph.shutil.which", return_value="/bin/codegraph"),
        patch("whub.services.codegraph.subprocess.run") as run,
    ):
        result = CliRunner().invoke(codegraph, catch_exceptions=False)

    assert result.exit_code == 0
    run.assert_called_once_with(
        ["/bin/codegraph", "init", str(project.resource._resolved_workspace_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert "init    local (CodeGraph)" in result.output


def test_missing_local_target_is_skipped(tmp_path) -> None:
    configured = manifest()
    project = configured.resolve_project("local")
    assert project is not None and project.resource is not None
    project.resource.codegraph = True
    project.resource._resolved_workspace_path = tmp_path / "missing"

    with (
        patch("whub.commands.codegraph.get_manifest", return_value=configured),
        patch("whub.services.codegraph.subprocess.run") as run,
    ):
        result = CliRunner().invoke(codegraph, catch_exceptions=False)

    assert result.exit_code == 0
    assert "skip    local (not found)" in result.output
    run.assert_not_called()


def test_excludes_codegraph_false() -> None:
    assert initialize_codegraph(manifest()) == []


def test_local_failure_does_not_stop_later_targets(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    configured = resolve_manifest(Manifest.model_validate(
        {
            "version": "2",
            "projects": [
                {
                    "name": "first",
                    "resource": {
                        "type": "symlink",
                        "workspace_path": "first",
                        "source": str(first),
                        "codegraph": True,
                    },
                },
                {
                    "name": "second",
                    "resource": {
                        "type": "symlink",
                        "workspace_path": "second",
                        "source": str(second),
                        "codegraph": True,
                    },
                },
            ],
        }
    ), tmp_path)
    configured.projects[0].resource._resolved_workspace_path = first
    configured.projects[1].resource._resolved_workspace_path = second

    with (
        patch("whub.commands.codegraph.get_manifest", return_value=configured),
        patch("whub.services.codegraph.shutil.which", return_value="/bin/codegraph"),
        patch(
            "whub.services.codegraph.subprocess.run",
            side_effect=[
                subprocess.CalledProcessError(1, [], stderr="failed"),
                subprocess.CompletedProcess([], 0),
            ],
        ),
    ):
        result = CliRunner().invoke(codegraph, catch_exceptions=False)

    assert result.exit_code == 0
    assert "first: CodeGraph init failed" in result.output
    assert "init    second (CodeGraph)" in result.output


def test_remote_init_uses_ssh() -> None:
    configured = manifest()
    project = configured.resolve_project("remote")
    assert project is not None and project.resource is not None
    project.resource.codegraph = True
    completed = subprocess.CompletedProcess(["ssh"], 0, stdout="", stderr="")

    with (
        patch("whub.commands.codegraph.get_manifest", return_value=configured),
        patch(
            "whub.services.codegraph.run_ssh_command", return_value=completed
        ) as run,
    ):
        result = CliRunner().invoke(codegraph, catch_exceptions=False)

    assert result.exit_code == 0
    # PATHはrun_ssh_command側のpreludeで解決するため、shell初期化の前置きを持たない
    assert run.call_args.args[1] == (
        f"codegraph init {configured.remote_path(project.resource)}"
    )
    assert "init    remote (CodeGraph)" in result.output


def test_workspace_root_is_not_initialized() -> None:
    configured = manifest()

    with (
        patch("whub.commands.codegraph.get_manifest", return_value=configured),
        patch("whub.services.codegraph.subprocess.run") as local_run,
        patch("whub.services.codegraph.run_ssh_command") as remote_run,
    ):
        result = CliRunner().invoke(codegraph, catch_exceptions=False)

    assert result.exit_code == 0
    local_run.assert_not_called()
    remote_run.assert_not_called()
