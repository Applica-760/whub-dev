"""Command builders for remote operations."""

from __future__ import annotations
import re
import shlex
import subprocess
from pathlib import Path
from whub.models import Host


# 非対話SSHのPATHに~/.local/binが含まれないため、規約として先頭へ付与する
PATH_PRELUDE = 'export PATH="$HOME/.local/bin:$PATH"; '


def with_path_prelude(command: str) -> str:
    return f"{PATH_PRELUDE}{command}"


def build_remote_exec_command(
    working_directory: str,
    arguments: tuple[str, ...],
) -> str:
    return with_path_prelude(
        f"cd {shlex.quote(working_directory)} && exec {shlex.join(arguments)}"
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
        "-i",
        identity,
        "-p",
        str(port),
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
            with_path_prelude(remote_command),
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


def run_ssh_command_bytes(
    host: Host,
    remote_command: str,
    *,
    timeout: int | None = None,
    batch_mode: bool = False,
    connect_timeout: int | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """stdoutをdecodeせず受け取る。tar等のbinary streamを取得するときに使う。"""
    return subprocess.run(
        build_ssh_command(
            host,
            with_path_prelude(remote_command),
            batch_mode=batch_mode,
            connect_timeout=connect_timeout,
        ),
        capture_output=True,
        timeout=timeout,
    )


def build_sshfs_command(
    host: Host,
    remote_path: str,
    mountpoint: Path,
    volname: str,
) -> list[str]:
    target, identity, port = ssh_target(host)
    options = [
        f"IdentityFile={identity}",
        f"port={port}",
        "reconnect",
        "ServerAliveInterval=60",
        "ServerAliveCountMax=3",
        "noappledouble",
        "noapplexattr",
        "defer_permissions",
        f"volname={volname}",
    ]
    return [
        "sshfs",
        f"{target}:{remote_path}",
        str(mountpoint),
        "-s",  # ADR 0007: single-threaded
        *(arg for option in options for arg in ("-o", option)),
    ]


def build_remote_hash_command(path: str) -> str:
    return f"sha256sum -- {shlex.quote(path)}"


def parse_sha256sum_output(output: str) -> str:
    hash_value, _, _ = output.strip().partition(" ")
    if len(hash_value) != 64:
        raise ValueError(f"unexpected sha256sum output: {output!r}")
    return hash_value


def remote_file_hash(
    host: Host,
    path: str,
    *,
    timeout: int | None = None,
) -> str | None:
    """pathのsha256を返す。未存在・実行失敗・想定外出力ではNone。"""
    result = run_ssh_command(
        host,
        build_remote_hash_command(path),
        batch_mode=True,
        connect_timeout=5,
        timeout=timeout,
    )
    if result.returncode != 0:
        return None
    try:
        return parse_sha256sum_output(result.stdout)
    except ValueError:
        return None


def build_remote_write_command(path: str) -> str:
    """標準入力の内容をpathへatomicに書き込むリモートシェルコマンドを返す。"""
    quoted = shlex.quote(path)
    tmp = shlex.quote(f"{path}.whub-tmp")
    return f"cat > {tmp} && mv -f {tmp} {quoted}"


def remote_write_file(
    host: Host,
    path: str,
    content: str,
    *,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_ssh_command(
        host,
        build_remote_write_command(path),
        input=content,
        batch_mode=True,
        connect_timeout=5,
        timeout=timeout,
    )


def build_remote_tar_command(root: str, relative_path: str) -> str:
    """root配下のrelative_pathをtar streamでstdoutへ出すコマンドを返す。

    rootが無ければcdが失敗して非0終了する。relative_pathが無い場合は
    「対象なし」であり異常ではないため、空出力のまま正常終了させる。
    """
    quoted_root = shlex.quote(root)
    quoted_relative = shlex.quote(relative_path)
    return (
        f"cd {quoted_root} && "
        f"if test -d {quoted_relative}; then tar cf - -- {quoted_relative}; fi"
    )


def _escape_scp_glob(path: str) -> str:
    # scpはリモートパスをglobとして解釈するため、リテラルパス扱いにする
    return re.sub(r"([\\*?\[\]])", r"\\\1", path)


def build_scp_command(
    host: Host,
    remote_path: str,
    local_dest: Path,
) -> list[str]:
    target, identity, port = ssh_target(host)
    return [
        "scp",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
        "-i",
        identity,
        "-P",
        str(port),  # scpのポート指定はsshと違い大文字
        f"{target}:{_escape_scp_glob(remote_path)}",
        str(local_dest),
    ]


def build_rsync_command(
    host: Host,
    local_src: str,
    remote_dest: str,
) -> list[str]:
    target, identity, port = ssh_target(host)
    return [
        "rsync",
        "-a",
        "-e",
        f"ssh -i {shlex.quote(identity)} -p {port}",
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
