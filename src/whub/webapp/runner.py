"""Detached process entry point for the whub web application."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

import uvicorn

from whub.webapp.server import create_app


@dataclass(frozen=True)
class AppProcessRecord:
    """PID record of a managed web application process."""

    pid: int
    port: int


def read_pid_record(pid_path: Path) -> AppProcessRecord | None:
    """Read a managed process PID record, if present."""
    if not pid_path.is_file():
        return None
    try:
        value = json.loads(pid_path.read_text())
        return AppProcessRecord(pid=int(value["pid"]), port=int(value["port"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid app pid file: {pid_path}") from error


def write_pid_record(pid_path: Path, port: int) -> None:
    """Write this process PID record for the managed web application."""
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(json.dumps({"pid": os.getpid(), "port": port}) + "\n")


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


def main() -> None:
    """Run the detached server process from command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--pid-path", type=Path, required=True)
    args = parser.parse_args()
    serve(args.dist_dir, args.port, args.pid_path)


# `whub app` launches this module as a detached child process with `python -m`.
if __name__ == "__main__":
    main()
