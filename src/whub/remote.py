"""Command builders for remote operations."""
from __future__ import annotations
import subprocess
from pathlib import Path
from whub.models import Host

def ssh_target(host: Host) -> tuple[str, str, int]:
    target = f"{host.user}@{host.hostname}"
    identity = str(Path(host.identity_file).expanduser())
    return target, identity, host.port

def build_ssh_command(
    host: Host,
    remote_command: str,
    *,
    tty: bool = False,
    batch_mode: bool = False,
    connect_timeout: int | None = None,
) -> list[str]:
    target, identity, port = ssh_target(host)
    return [
        "ssh",
        *(["-t"] if tty else []),
        *(["-o", "BatchMode=yes"] if batch_mode else []),
        *(
            ["-o", f"ConnectTimeout={connect_timeout}"]
            if connect_timeout is not None
            else []
        ),
        "-i", identity,
        "-p", str(port),
        target,
        remote_command,
    ]


def run_ssh_command(
    host: Host,
    remote_command: str,
    *,
    input: str | None = None,
    timeout: int | None = None,
    tty: bool = False,
    batch_mode: bool = False,
    connect_timeout: int | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        build_ssh_command(
            host,
            remote_command,
            tty=tty,
            batch_mode=batch_mode,
            connect_timeout=connect_timeout,
        ),
        input=input,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def build_rsync_command(
    host: Host,
    local_src: str,
    remote_dest: str,
) -> list[str]:
    target, identity, port = ssh_target(host)
    return [
        "rsync", "-a",
        "-e", f"ssh -i {identity} -p {port}",
        f"{local_src}/",
        f"{target}:{remote_dest}/",
    ]


def run_rsync_command(
    host: Host,
    local_src: str,
    remote_dest: str,
    *,
    timeout: int | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        build_rsync_command(host, local_src, remote_dest),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )
