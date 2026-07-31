"""tmux session naming and remote shell snippet builders."""

from __future__ import annotations
import shlex
from pathlib import Path


def session_name(*parts: str) -> str:
    """Return one tmux-safe whub session name from stable identifiers."""
    if not parts or any(not part for part in parts):
        raise ValueError("tmux session name requires non-empty parts")
    return "whub-" + "-".join(
        part.replace(".", "-").replace(":", "-") for part in parts
    )


def session_target(name: str) -> str:
    """Return an exact tmux session target without prefix interpretation."""
    return f"={name}"


def tmux_command(*args: str, socket: Path | None = None) -> list[str]:
    """Build one tmux argv, optionally scoped to a private socket."""
    return ["tmux", *(["-S", str(socket)] if socket is not None else []), *args]


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
