"""`whub.core.remote`の仕様テスト。

検証するケース:
1. `ssh_target()`は`user@hostname`、展開済みidentity path、portを返す。
2. `build_remote_exec_command()`はPATH preludeに続けてworkdirへ`cd`し、引数列をquoteして`exec`する。
3. `build_ssh_command()`はidentity/port/target/remote commandを含む基本SSH argvを作る。
4. `build_ssh_command()`は`tty`、`batch_mode`、`connect_timeout`を必要時だけ追加する。
5. `run_ssh_command()`はPATH preludeを付けたSSH argvと実行オプションを`subprocess.run()`へ渡す。
6. `build_sshfs_command()`はremote path、mountpoint、identity/port、`-s`、mount optionsを含む。
7. `build_scp_command()`はBatchMode/ConnectTimeout、identity、大文字`-P` port、local destを含む。
8. `build_scp_command()`はremote path中のglob文字をescapeする。
9. `build_rsync_command()`は`rsync -a`、ssh transport、`local_src/`、`target:remote_dest/`を作る。
10. `run_rsync_command()`はrsync argvと実行オプションを`subprocess.run()`へ渡す。
11. `build_remote_hash_command()`は`sha256sum --`にquote済みpathを続けたコマンドを返す。
12. `parse_sha256sum_output()`はsha256sum出力からhashを抽出し、想定外の出力を拒否する。
13. `remote_file_hash()`は成功時にhashを返し、コマンド失敗・想定外出力ではNoneを返す。
14. `build_remote_write_command()`は標準入力をtmpへ書いてからmvするコマンドを返す。
15. `remote_write_file()`はcontentをinputとしてssh経由でatomic書き込みコマンドを実行する。

検証しないケース:
1. 実SSH接続・実scp・実rsync・実sshfsの成功失敗。
2. OpenSSHやrsync自体のquote解釈。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import whub.core.remote as remote_module
from whub.models import Host
from whub.core.remote import (
    build_remote_exec_command,
    build_remote_hash_command,
    build_remote_write_command,
    build_rsync_command,
    build_scp_command,
    build_ssh_command,
    build_sshfs_command,
    parse_sha256sum_output,
    remote_file_hash,
    remote_write_file,
    run_rsync_command,
    run_ssh_command,
    ssh_target,
    with_path_prelude,
)


def _host(identity_file: str = "~/.ssh/id_home") -> Host:
    return Host(
        hostname="home.example.com",
        user="takumi",
        port=2222,
        identity_file=identity_file,
        mount_root="/srv",
    )


class TestRemoteSpec:
    def test_ssh_target_returns_target_identity_and_port(self) -> None:
        # ケース1
        target, identity, port = ssh_target(_host())

        assert target == "takumi@home.example.com"
        assert identity == str(Path("~/.ssh/id_home").expanduser())
        assert port == 2222

    def test_build_remote_exec_command_changes_directory_and_execs_quoted_arguments(
        self,
    ) -> None:
        # ケース2
        command = build_remote_exec_command(
            "/srv/project path",
            ("python", "-c", "print('hello world')"),
        )

        assert command == (
            'export PATH="$HOME/.local/bin:$PATH"; '
            "cd '/srv/project path' && exec python -c 'print('\"'\"'hello world'\"'\"')'"
        )

    def test_build_ssh_command_builds_basic_argv(self) -> None:
        # ケース3
        command = build_ssh_command(_host(), "echo ok")

        assert command == [
            "ssh",
            "-i",
            str(Path("~/.ssh/id_home").expanduser()),
            "-p",
            "2222",
            "takumi@home.example.com",
            "echo ok",
        ]

    def test_build_ssh_command_adds_optional_flags_only_when_requested(self) -> None:
        # ケース4
        base = build_ssh_command(_host(), "echo ok")
        assert "-t" not in base
        assert "BatchMode=yes" not in base
        assert "ConnectTimeout=5" not in base

        command = build_ssh_command(
            _host(),
            "echo ok",
            tty=True,
            batch_mode=True,
            connect_timeout=5,
        )

        assert "-t" in command
        assert "BatchMode=yes" in command
        assert "ConnectTimeout=5" in command

    def test_run_ssh_command_delegates_to_subprocess_run(self) -> None:
        # ケース5
        completed = subprocess.CompletedProcess([], 0, "out", "")
        with patch.object(
            remote_module.subprocess,
            "run",
            return_value=completed,
        ) as execute:
            result = run_ssh_command(
                _host(),
                "cat > file",
                input="content",
                timeout=10,
                tty=True,
                batch_mode=True,
                connect_timeout=5,
                check=True,
            )

        assert result is completed
        assert execute.call_args.args[0] == build_ssh_command(
            _host(),
            'export PATH="$HOME/.local/bin:$PATH"; cat > file',
            tty=True,
            batch_mode=True,
            connect_timeout=5,
        )
        assert execute.call_args.kwargs["input"] == "content"
        assert execute.call_args.kwargs["timeout"] == 10
        assert execute.call_args.kwargs["check"]

    def test_build_sshfs_command_builds_mount_argv(self) -> None:
        # ケース6
        command = build_sshfs_command(
            _host(),
            "/srv/remote",
            Path("/tmp/mount"),
            "whub-remote",
        )

        assert command[:4] == [
            "sshfs",
            "takumi@home.example.com:/srv/remote",
            "/tmp/mount",
            "-s",
        ]
        assert f"IdentityFile={Path('~/.ssh/id_home').expanduser()}" in command
        assert "port=2222" in command
        assert "reconnect" in command
        assert "volname=whub-remote" in command

    def test_build_scp_command_builds_batch_argv(self) -> None:
        # ケース7
        command = build_scp_command(_host(), "/srv/remote/out.nc", Path("/tmp/out.nc"))

        assert command == [
            "scp",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            "-i",
            str(Path("~/.ssh/id_home").expanduser()),
            "-P",
            "2222",
            "takumi@home.example.com:/srv/remote/out.nc",
            "/tmp/out.nc",
        ]

    def test_build_scp_command_escapes_remote_glob_characters(self) -> None:
        # ケース8
        command = build_scp_command(_host(), "/srv/[run]?/*.nc", Path("/tmp/out.nc"))

        assert r"takumi@home.example.com:/srv/\[run\]\?/\*.nc" in command

    def test_build_rsync_command_builds_copy_argv(self) -> None:
        # ケース9
        command = build_rsync_command(
            _host(), "/tmp/skills", "/srv/project/.agents/skills"
        )

        assert command == [
            "rsync",
            "-a",
            "-e",
            f"ssh -i {Path('~/.ssh/id_home').expanduser()} -p 2222",
            "/tmp/skills/",
            "takumi@home.example.com:/srv/project/.agents/skills/",
        ]

    def test_build_rsync_command_quotes_identity_path(self) -> None:
        # ケース9b
        host = _host("~/Library/Application Support/whub/id home")
        command = build_rsync_command(host, "/tmp/skills", "/srv/project")

        assert (
            f"ssh -i '{Path('~/Library/Application Support/whub/id home').expanduser()}' -p 2222"
            in command
        )

    def test_run_rsync_command_delegates_to_subprocess_run(self) -> None:
        # ケース10
        completed = subprocess.CompletedProcess([], 0, "out", "")
        with patch.object(
            remote_module.subprocess,
            "run",
            return_value=completed,
        ) as execute:
            result = run_rsync_command(
                _host(),
                "/tmp/skills",
                "/srv/project/.agents/skills",
                timeout=30,
                check=True,
            )

        assert result is completed
        assert execute.call_args.args[0] == build_rsync_command(
            _host(), "/tmp/skills", "/srv/project/.agents/skills"
        )
        assert execute.call_args.kwargs["timeout"] == 30
        assert execute.call_args.kwargs["check"]

    def test_build_remote_hash_command_builds_sha256sum_argv(self) -> None:
        # ケース11
        command = build_remote_hash_command("/srv/remote/out.nc")

        assert command == "sha256sum -- /srv/remote/out.nc"

    def test_build_remote_hash_command_quotes_path(self) -> None:
        # ケース11b
        command = build_remote_hash_command("/srv/remote/file with space.md")

        assert command == "sha256sum -- '/srv/remote/file with space.md'"

    def test_parse_sha256sum_output_extracts_hash(self) -> None:
        # ケース12
        digest = "a" * 64
        assert parse_sha256sum_output(f"{digest}  out.nc\n") == digest

    def test_parse_sha256sum_output_rejects_unexpected_output(self) -> None:
        # ケース12b
        for output in ("", "not a hash\n", "abc  out.nc\n"):
            with pytest.raises(ValueError):
                parse_sha256sum_output(output)

    def test_remote_file_hash_returns_hash_on_success(self) -> None:
        # ケース13
        digest = "b" * 64
        completed = subprocess.CompletedProcess([], 0, f"{digest}  out.nc\n", "")
        with patch.object(
            remote_module.subprocess, "run", return_value=completed
        ) as execute:
            result = remote_file_hash(_host(), "/srv/remote/out.nc", timeout=5)

        assert result == digest
        assert execute.call_args.args[0] == build_ssh_command(
            _host(),
            with_path_prelude(build_remote_hash_command("/srv/remote/out.nc")),
            batch_mode=True,
            connect_timeout=5,
        )

    def test_remote_file_hash_returns_none_on_failure_or_bad_output(self) -> None:
        # ケース13b
        with patch.object(
            remote_module.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 1, "", "no such file"),
        ):
            assert remote_file_hash(_host(), "/missing") is None

        with patch.object(
            remote_module.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "garbage\n", ""),
        ):
            assert remote_file_hash(_host(), "/srv/remote/out.nc") is None

    def test_build_remote_write_command_writes_tmp_then_moves(self) -> None:
        # ケース14
        command = build_remote_write_command("/srv/remote/out.nc")

        assert command == "cat > /srv/remote/out.nc.whub-tmp && mv -f /srv/remote/out.nc.whub-tmp /srv/remote/out.nc"

    def test_remote_write_file_sends_content_via_atomic_write_command(self) -> None:
        # ケース15
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(
            remote_module.subprocess, "run", return_value=completed
        ) as execute:
            result = remote_write_file(
                _host(), "/srv/remote/out.nc", "new content", timeout=10
            )

        assert result is completed
        assert execute.call_args.args[0] == build_ssh_command(
            _host(),
            with_path_prelude(build_remote_write_command("/srv/remote/out.nc")),
            batch_mode=True,
            connect_timeout=5,
        )
        assert execute.call_args.kwargs["input"] == "new content"
        assert execute.call_args.kwargs["timeout"] == 10
