"""Command builders for remote operations."""
from __future__ import annotations
import shlex
from pathlib import Path
from whub.models import Host

def build_remote_exec_command(
    working_directory: str,
    arguments: tuple[str, ...],
) -> str:
    return (
        f"cd {shlex.quote(working_directory)}"
        f" && exec {shlex.join(arguments)}"
    )

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
