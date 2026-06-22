"""Command builders for remote operations."""
from __future__ import annotations
from pathlib import Path
from whub.models import Host

def ssh_target(host: Host) -> tuple[str, str, int]:
    target = f"{host.user}@{host.hostname}"
    identity = str(Path(host.identity_file).expanduser())
    return target, identity, host.port

def _option_args(options: tuple[str, ...]) -> list[str]:
    return [arg for option in options for arg in ("-o", option)]

def build_ssh_command(
    host: Host,
    remote_command: str,
    *,
    tty: bool = False,
    options: tuple[str, ...] = (),
) -> list[str]:
    target, identity, port = ssh_target(host)
    return [
        "ssh",
        *(["-t"] if tty else []),
        *_option_args(options),
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
