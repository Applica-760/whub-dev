"""whub app — manage the local web application server."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import click

from whub.core.context import current_context
from whub.webapp.resources import (
    AppResourceError,
    development_app_source,
    packaged_app_dist,
)
from whub.webapp.runner import AppProcessRecord, read_pid_record, remove_pid_record

DEV_PORT = 8712
DEV_API_PORT = 8713


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


def _stop_process_groups(processes: dict[str, int]) -> None:
    groups: set[int] = set()
    for pid in processes.values():
        try:
            groups.add(os.getpgid(pid))
        except ProcessLookupError:
            continue
    if not groups:
        return
    for process_group in groups:
        try:
            os.killpg(process_group, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(0.1)
    for process_group in groups:
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            continue
        os.killpg(process_group, signal.SIGKILL)


@click.group(invoke_without_command=True)
@click.option("--port", type=int, default=8710, show_default=True)
@click.pass_context
def app(ctx: click.Context, port: int) -> None:
    """Start or stop the local web app server."""
    if ctx.invoked_subcommand is not None:
        return

    context = current_context()
    try:
        dist_dir = packaged_app_dist()
    except AppResourceError as error:
        raise click.ClickException(str(error)) from error

    pid_path = context.app_pid_path
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
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    click.echo(f"app starting: http://127.0.0.1:{port}")


@app.command()
@click.option("--dev", "dev_mode", is_flag=True, help="Stop the development server.")
def down(dev_mode: bool) -> None:
    """Stop a managed local web app server."""
    context = current_context()
    pid_path = context.app_dev_pid_path if dev_mode else context.app_pid_path
    name = "app dev" if dev_mode else "app"
    process = _read_running_process(pid_path)
    if process is None:
        click.echo(f"{name} not running")
        return

    try:
        process_group = os.getpgid(process.pid)
        os.killpg(process_group, signal.SIGTERM)
    except ProcessLookupError:
        remove_pid_record(pid_path, expected_pid=process.pid)
        click.echo(f"{name} stopped")
        return
    time.sleep(0.1)
    if _is_running(process.pid):
        try:
            os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if dev_mode:
        _stop_process_groups(process.processes)
    remove_pid_record(pid_path, expected_pid=process.pid)
    click.echo(f"{name} stopped")


@app.command()
def dev() -> None:
    """Start the local web app with HMR and API reload."""
    context = current_context()
    pid_path = context.app_dev_pid_path
    process = _read_running_process(pid_path)
    if process is not None:
        click.echo(f"app dev already running: http://127.0.0.1:{process.port}")
        return

    try:
        app_dir = development_app_source()
    except AppResourceError as error:
        raise click.ClickException(str(error)) from error

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "whub.webapp.runner",
            "--dev",
            "--app-dir",
            str(app_dir),
            "--port",
            str(DEV_PORT),
            "--api-port",
            str(DEV_API_PORT),
            "--pid-path",
            str(pid_path),
        ],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    click.echo(f"app dev starting: http://127.0.0.1:{DEV_PORT}")
