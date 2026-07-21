"""Detached process entry point for the whub web application."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn

from whub.webapp.server import create_app


@dataclass(frozen=True)
class AppProcessRecord:
    """PID record of a managed web application process."""

    pid: int
    port: int
    mode: str = "normal"
    processes: dict[str, int] = field(default_factory=dict)


def read_pid_record(pid_path: Path) -> AppProcessRecord | None:
    """Read a managed process PID record, if present."""
    if not pid_path.is_file():
        return None
    try:
        value = json.loads(pid_path.read_text())
        return AppProcessRecord(
            pid=int(value["pid"]),
            port=int(value["port"]),
            mode=str(value.get("mode", "normal")),
            processes={
                name: int(pid) for name, pid in value.get("processes", {}).items()
            },
        )
    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        raise ValueError(f"invalid app pid file: {pid_path}") from error


def write_pid_record(
    pid_path: Path,
    port: int,
    mode: str = "normal",
    processes: dict[str, int] | None = None,
) -> None:
    """Write this process PID record for the managed web application."""
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "port": port,
                "mode": mode,
                "processes": processes or {"server": os.getpid()},
            }
        )
        + "\n"
    )


def remove_pid_record(pid_path: Path, expected_pid: int | None = None) -> None:
    """Remove a PID record, optionally only when it belongs to EXPECTED_PID."""
    if expected_pid is not None:
        try:
            process = read_pid_record(pid_path)
        except ValueError:
            return
        if process is None or process.pid != expected_pid:
            return
    pid_path.unlink(missing_ok=True)


def serve(dist_dir: Path, port: int, pid_path: Path) -> None:
    """Run uvicorn and maintain the managed process record."""
    process_id = os.getpid()
    write_pid_record(pid_path, port)
    try:
        uvicorn.run(
            create_app(dist_dir),
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
    finally:
        remove_pid_record(pid_path, expected_pid=process_id)


def _stop_process_group(process: subprocess.Popen[object]) -> None:
    if process.poll() is not None:
        return
    try:
        process_group = os.getpgid(process.pid)
        os.killpg(process_group, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def serve_dev(app_dir: Path, port: int, api_port: int, pid_path: Path) -> None:
    """Run Vite and the reloading API server as one managed process group."""
    process_id = os.getpid()
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "whub.webapp.server:create_api_app",
            "--factory",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        cwd=app_dir.parent,
        start_new_session=True,
    )
    try:
        vite = subprocess.Popen(
            [
                "npm",
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--strictPort",
            ],
            cwd=app_dir,
            start_new_session=True,
        )
    except BaseException:
        _stop_process_group(api)
        raise
    children = [api, vite]
    write_pid_record(
        pid_path,
        port,
        mode="dev",
        processes={"api": children[0].pid, "vite": children[1].pid},
    )

    def stop_children(signum: int, frame: object) -> None:
        del signum, frame
        raise SystemExit

    previous_handlers = {
        signum: signal.signal(signum, stop_children)
        for signum in (signal.SIGTERM, signal.SIGINT)
    }
    try:
        while all(child.poll() is None for child in children):
            time.sleep(0.1)
    finally:
        for child in children:
            _stop_process_group(child)
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        remove_pid_record(pid_path, expected_pid=process_id)


def main() -> None:
    """Run the detached server process from command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--app-dir", type=Path)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--api-port", type=int)
    parser.add_argument("--pid-path", type=Path, required=True)
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    if args.dev:
        if args.app_dir is None or args.api_port is None:
            parser.error("--dev requires --app-dir and --api-port")
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        serve_dev(args.app_dir, args.port, args.api_port, args.pid_path)
    elif args.dist_dir is None:
        parser.error("--dist-dir is required without --dev")
    else:
        serve(args.dist_dir, args.port, args.pid_path)


# `whub app` launches this module as a detached child process with `python -m`.
if __name__ == "__main__":
    main()
