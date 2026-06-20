"""whub shell-init — emit shell function and tab completion for eval."""

from __future__ import annotations

import click

_SHELL_FUNC = r"""
whub() {
    if [ "$1" = "cd" ] && [ -n "$2" ]; then
        local _out _rc
        _out="$(command whub cd "$2")"
        _rc=$?
        if [ $_rc -eq 0 ]; then
            builtin cd "$_out"
        elif [ $_rc -eq 100 ]; then
            eval "$_out"
        else
            echo "$_out" >&2
            return $_rc
        fi
    else
        command whub "$@"
    fi
}
"""

_ZSH_COMPLETION = r"""
eval "$(_WHUB_COMPLETE=zsh_source command whub)"
"""


@click.command("shell-init")
@click.option("--shell", "shell_type", type=click.Choice(["zsh"]), default="zsh")
def shell_init(shell_type: str) -> None:
    """Emit shell function and completion setup for eval."""
    click.echo(_SHELL_FUNC.strip())
    if shell_type == "zsh":
        click.echo(_ZSH_COMPLETION.strip())
