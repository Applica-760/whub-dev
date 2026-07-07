"""`whub.tmux`の仕様テスト。

検証するケース:
1. `session_name()`はproject名に`whub-` prefixを付ける。
2. `session_name()`はtmuxで使えない`.`と`:`を`-`へ置換する。
3. `build_shell_command()`はtmux未導入時に対象workdirへ`cd`してlogin shellへfallbackする。
4. `build_shell_command()`は既存sessionがあればそのsessionへattachする。
5. `build_shell_command()`は新規session作成時にmouse/history-limit/destroy-unattached/workdirを設定する。
6. `build_shell_command()`はsession名とworkdirをshell quoteする。

検証しないケース:
1. 実tmuxの起動・attach成功。
2. リモートshell上での実行結果。
3. tmux各optionの意味そのもの。
"""
from __future__ import annotations

import unittest

from whub.tmux import build_shell_command, session_name


class TmuxSpecTest(unittest.TestCase):
    def test_session_name_adds_prefix(self) -> None:
        # ケース1
        self.assertEqual(session_name("project"), "whub-project")

    def test_session_name_replaces_tmux_unsafe_characters(self) -> None:
        # ケース2
        self.assertEqual(session_name("project.name:task"), "whub-project-name-task")

    def test_build_shell_command_falls_back_when_tmux_is_missing(self) -> None:
        # ケース3
        command = build_shell_command("whub-project", "/srv/project")

        self.assertIn("if ! command -v tmux", command)
        self.assertIn("cd /srv/project && exec $SHELL -l", command)

    def test_build_shell_command_attaches_existing_session(self) -> None:
        # ケース4
        command = build_shell_command("whub-project", "/srv/project")

        self.assertIn("tmux has-session -t =whub-project", command)
        self.assertIn("exec tmux new-session -t whub-project", command)

    def test_build_shell_command_creates_configured_new_session(self) -> None:
        # ケース5
        command = build_shell_command("whub-project", "/srv/project")

        self.assertIn("set-option -g mouse on", command)
        self.assertIn("set-option -g history-limit 50000", command)
        self.assertIn("set-option destroy-unattached on", command)
        self.assertIn("new-session -s whub-project -c /srv/project", command)

    def test_build_shell_command_quotes_session_and_workdir(self) -> None:
        # ケース6
        command = build_shell_command("whub project", "/srv/project path")

        self.assertIn("tmux has-session -t ='whub project'", command)
        self.assertIn("cd '/srv/project path' && exec $SHELL -l", command)
        self.assertIn("new-session -s 'whub project' -c '/srv/project path'", command)


if __name__ == "__main__":
    unittest.main()
