"""tmux session naming and remote shell snippet builders."""

from __future__ import annotations
import shlex


def session_name(project_name: str) -> str:
    # tmuxのセッション名は"."と":"を使えない
    return "whub-" + project_name.replace(".", "-").replace(":", "-")


def build_shell_command(session_name: str, workdir: str) -> str:
    # history-limitはnew-sessionより前に設定しないと最初のpaneに効かない
    session = shlex.quote(session_name)
    path = shlex.quote(workdir)
    return (
        "if ! command -v tmux >/dev/null 2>&1; then "
        "echo 'whub: tmux not found, falling back to plain shell' >&2; "
        f"cd {path} && exec $SHELL -l; "
        f"elif tmux has-session -t ={session} 2>/dev/null; then "
        f"exec tmux new-session -t {session} \\; set-option destroy-unattached on; "
        "else "
        "exec tmux start-server \\; "
        "set-option -g mouse on \\; set-option -g history-limit 50000 \\; "
        f"new-session -s {session} -c {path}; "
        "fi"
    )
