"""`whub.remote`の仕様テスト。

検証するケース:
1. `ssh_target()`は`user@hostname`、展開済みidentity path、portを返す。
2. `build_remote_exec_command()`はworkdirへ`cd`してから引数列をquoteして`exec`する。
3. `build_ssh_command()`はidentity/port/target/remote commandを含む基本SSH argvを作る。
4. `build_ssh_command()`は`tty`、`batch_mode`、`connect_timeout`を必要時だけ追加する。
5. `run_ssh_command()`はSSH argvと実行オプションを`subprocess.run()`へ渡す。
6. `build_sshfs_command()`はremote path、mountpoint、identity/port、`-s`、mount optionsを含む。
7. `build_scp_command()`はBatchMode/ConnectTimeout、identity、大文字`-P` port、local destを含む。
8. `build_scp_command()`はremote path中のglob文字をescapeする。
9. `build_rsync_command()`は`rsync -a`、ssh transport、`local_src/`、`target:remote_dest/`を作る。
10. `run_rsync_command()`はrsync argvと実行オプションを`subprocess.run()`へ渡す。

検証しないケース:
1. 実SSH接続・実scp・実rsync・実sshfsの成功失敗。
2. OpenSSHやrsync自体のquote解釈。
3. identity pathに空白がある場合のshell安全性改善。
4. `build_rsync_command()`のidentity path未quote問題の修正。
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import whub.remote as remote_module
from whub.models import Host
from whub.remote import (
    build_remote_exec_command,
    build_rsync_command,
    build_scp_command,
    build_ssh_command,
    build_sshfs_command,
    run_rsync_command,
    run_ssh_command,
    ssh_target,
)


def _host() -> Host:
    return Host(
        hostname="home.example.com",
        user="takumi",
        port=2222,
        identity_file="~/.ssh/id_home",
    )


class RemoteSpecTest(unittest.TestCase):
    def test_ssh_target_returns_target_identity_and_port(self) -> None:
        # ケース1
        target, identity, port = ssh_target(_host())

        self.assertEqual(target, "takumi@home.example.com")
        self.assertEqual(identity, str(Path("~/.ssh/id_home").expanduser()))
        self.assertEqual(port, 2222)

    def test_build_remote_exec_command_changes_directory_and_execs_quoted_arguments(self) -> None:
        # ケース2
        command = build_remote_exec_command(
            "/srv/project path",
            ("python", "-c", "print('hello world')"),
        )

        self.assertEqual(
            command,
            "cd '/srv/project path' && exec python -c 'print('\"'\"'hello world'\"'\"')'",
        )

    def test_build_ssh_command_builds_basic_argv(self) -> None:
        # ケース3
        command = build_ssh_command(_host(), "echo ok")

        self.assertEqual(
            command,
            [
                "ssh",
                "-i", str(Path("~/.ssh/id_home").expanduser()),
                "-p", "2222",
                "takumi@home.example.com",
                "echo ok",
            ],
        )

    def test_build_ssh_command_adds_optional_flags_only_when_requested(self) -> None:
        # ケース4
        base = build_ssh_command(_host(), "echo ok")
        self.assertNotIn("-t", base)
        self.assertNotIn("BatchMode=yes", base)
        self.assertNotIn("ConnectTimeout=5", base)

        command = build_ssh_command(
            _host(),
            "echo ok",
            tty=True,
            batch_mode=True,
            connect_timeout=5,
        )

        self.assertIn("-t", command)
        self.assertIn("BatchMode=yes", command)
        self.assertIn("ConnectTimeout=5", command)

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

        self.assertIs(result, completed)
        self.assertEqual(
            execute.call_args.args[0],
            build_ssh_command(
                _host(),
                "cat > file",
                tty=True,
                batch_mode=True,
                connect_timeout=5,
            ),
        )
        self.assertEqual(execute.call_args.kwargs["input"], "content")
        self.assertEqual(execute.call_args.kwargs["timeout"], 10)
        self.assertTrue(execute.call_args.kwargs["check"])

    def test_build_sshfs_command_builds_mount_argv(self) -> None:
        # ケース6
        command = build_sshfs_command(
            _host(),
            "/srv/remote",
            Path("/tmp/mount"),
            "whub-remote",
        )

        self.assertEqual(command[:4], ["sshfs", "takumi@home.example.com:/srv/remote", "/tmp/mount", "-s"])
        self.assertIn(f"IdentityFile={Path('~/.ssh/id_home').expanduser()}", command)
        self.assertIn("port=2222", command)
        self.assertIn("reconnect", command)
        self.assertIn("volname=whub-remote", command)

    def test_build_scp_command_builds_batch_argv(self) -> None:
        # ケース7
        command = build_scp_command(_host(), "/srv/remote/out.nc", Path("/tmp/out.nc"))

        self.assertEqual(
            command,
            [
                "scp",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=5",
                "-i", str(Path("~/.ssh/id_home").expanduser()),
                "-P", "2222",
                "takumi@home.example.com:/srv/remote/out.nc",
                "/tmp/out.nc",
            ],
        )

    def test_build_scp_command_escapes_remote_glob_characters(self) -> None:
        # ケース8
        command = build_scp_command(_host(), "/srv/[run]?/*.nc", Path("/tmp/out.nc"))

        self.assertIn(r"takumi@home.example.com:/srv/\[run\]\?/\*.nc", command)

    def test_build_rsync_command_builds_copy_argv(self) -> None:
        # ケース9
        command = build_rsync_command(_host(), "/tmp/skills", "/srv/project/.agents/skills")

        self.assertEqual(
            command,
            [
                "rsync", "-a",
                "-e", f"ssh -i {Path('~/.ssh/id_home').expanduser()} -p 2222",
                "/tmp/skills/",
                "takumi@home.example.com:/srv/project/.agents/skills/",
            ],
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

        self.assertIs(result, completed)
        self.assertEqual(
            execute.call_args.args[0],
            build_rsync_command(_host(), "/tmp/skills", "/srv/project/.agents/skills"),
        )
        self.assertEqual(execute.call_args.kwargs["timeout"], 30)
        self.assertTrue(execute.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()
