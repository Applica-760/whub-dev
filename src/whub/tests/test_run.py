from __future__ import annotations
import importlib
import subprocess
import unittest
from unittest.mock import patch
from click.testing import CliRunner
from whub.models import Manifest
from whub.remote import build_remote_exec_command, build_ssh_command


run_module = importlib.import_module("whub.commands.run")


class RemoteCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.host = Manifest.model_validate({
            "version": "1",
            "hosts": {
                "server": {
                    "hostname": "example.com",
                    "user": "user",
                    "port": 2222,
                    "identity_file": "~/.ssh/test-key",
                },
            },
        }).hosts["server"]

    def test_preserves_remote_argument_boundaries(self) -> None:
        command = build_remote_exec_command(
            "/srv/project with space",
            ("printf", "", "two words", "$HOME", "quote's"),
        )

        self.assertEqual(
            command,
            "cd '/srv/project with space' && exec "
            "printf '' 'two words' '$HOME' 'quote'\"'\"'s'",
        )

    def test_builds_explicit_ssh_options(self) -> None:
        command = build_ssh_command(
            self.host,
            "pwd",
            tty=True,
            batch_mode=True,
            connect_timeout=5,
        )

        self.assertEqual(command[:6], [
            "ssh",
            "-t",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
        ])


class RunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = Manifest.model_validate({
            "version": "1",
            "hosts": {
                "server": {
                    "hostname": "example.com",
                    "user": "user",
                    "port": 2222,
                    "identity_file": "/tmp/key",
                },
            },
            "resources": {
                "symlinks": [{
                    "name": "local",
                    "workspace_path": "local",
                    "source": "/tmp/local",
                }],
                "remotes": [{
                    "name": "remote",
                    "host": "server",
                    "path": "/srv/project",
                }],
            },
        })

    def test_runs_without_tty_and_returns_remote_exit_code(self) -> None:
        completed = subprocess.CompletedProcess([], 17)
        with patch.object(
            run_module.subprocess,
            "run",
            return_value=completed,
        ) as execute:
            result = CliRunner().invoke(
                run_module.run,
                ["remote", "git", "status", "--short"],
                obj={"manifest": self.manifest},
            )

        self.assertEqual(result.exit_code, 17)
        execute.assert_called_once_with([
            "ssh",
            "-i", "/tmp/key",
            "-p", "2222",
            "user@example.com",
            "cd /srv/project && exec git status --short",
        ])

    def test_tty_option_allocates_terminal(self) -> None:
        with patch.object(
            run_module.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0),
        ) as execute:
            result = CliRunner().invoke(
                run_module.run,
                ["--tty", "remote", "bash"],
                obj={"manifest": self.manifest},
            )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(execute.call_args.args[0][1], "-t")

    def test_command_option_named_tty_is_preserved(self) -> None:
        with patch.object(
            run_module.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0),
        ) as execute:
            result = CliRunner().invoke(
                run_module.run,
                ["remote", "command", "--tty"],
                obj={"manifest": self.manifest},
            )

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("-t", execute.call_args.args[0])
        self.assertEqual(
            execute.call_args.args[0][-1],
            "cd /srv/project && exec command --tty",
        )

    def test_rejects_unknown_and_local_resources(self) -> None:
        for resource, message in (
            ("missing", "unknown resource: missing"),
            ("local", "resource is not remote: local"),
        ):
            with self.subTest(resource=resource):
                with patch.object(run_module.subprocess, "run") as execute:
                    result = CliRunner().invoke(
                        run_module.run,
                        [resource, "pwd"],
                        obj={"manifest": self.manifest},
                    )

                self.assertEqual(result.exit_code, 1)
                self.assertIn(message, result.output)
                execute.assert_not_called()

    def test_requires_command(self) -> None:
        result = CliRunner().invoke(
            run_module.run,
            ["remote"],
            obj={"manifest": self.manifest},
        )

        self.assertEqual(result.exit_code, 2)
        self.assertIn("Missing argument 'COMMAND...'", result.output)


if __name__ == "__main__":
    unittest.main()
