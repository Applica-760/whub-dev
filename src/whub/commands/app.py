"""whub app — manage the local web application server."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import click

from whub.core.paths import app_dist_path, app_pid_path
from whub.webapp.runner import AppProcessRecord, read_pid_record, remove_pid_record


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_running_process(pid_path: Path) -> AppProcessRecord | None:
    try:
        process = read_pid_record(pid_path)
    except ValueError:
        remove_pid_record(pid_path)
        return None
    if process is not None and not _is_running(process.pid):
        remove_pid_record(pid_path, expected_pid=process.pid)
        return None
    return process


@click.group(invoke_without_command=True)
@click.option("--port", type=int, default=8710, show_default=True)
@click.pass_context
def app(ctx: click.Context, port: int) -> None:
    """Start or stop the local web app server."""
    if ctx.invoked_subcommand is not None:
        return

    dist_dir = app_dist_path()
    if not (dist_dir / "index.html").is_file():
        raise click.ClickException(
            "web app is not built; run `cd app && npm install && npm run build`"
        )

    pid_path = app_pid_path()
    process = _read_running_process(pid_path)
    if process is not None:
        click.echo(f"app already running: http://127.0.0.1:{process.port}")
        return

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "whub.webapp.runner",
            "--dist-dir",
            str(dist_dir),
            "--port",
            str(port),
            "--pid-path",
            str(pid_path),
        ],
        start_new_session=True,
    )
    click.echo(f"app starting: http://127.0.0.1:{port}")


@app.command()
def down() -> None:
    """Stop the managed local web app server."""
    pid_path = app_pid_path()
    process = _read_running_process(pid_path)
    if process is None:
        click.echo("app not running")
        return

    try:
        process_group = os.getpgid(process.pid)
        os.killpg(process_group, signal.SIGTERM)
    except ProcessLookupError:
        remove_pid_record(pid_path, expected_pid=process.pid)
        click.echo("app stopped")
        return
    time.sleep(0.1)
    if _is_running(process.pid):
        try:
            os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:
            pass
    remove_pid_record(pid_path, expected_pid=process.pid)
    click.echo("app stopped")


@app.command()
def dev() -> None:
    """Start the local web app with HMR and API reload."""
    pid_path = app_pid_path()
    process = _read_running_process(pid_path)
    if process is not None:
        click.echo(f"app already running: http://127.0.0.1:{process.port}")
        return

    app_dir = app_dist_path().parent
    if not (app_dir / "package.json").is_file():
        raise click.ClickException(f"web app source is missing: {app_dir}")

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "whub.webapp.runner",
            "--dev",
            "--app-dir",
            str(app_dir),
            "--port",
            "8710",
            "--api-port",
            "8711",
            "--pid-path",
            str(pid_path),
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    click.echo("app starting: http://127.0.0.1:8710")
