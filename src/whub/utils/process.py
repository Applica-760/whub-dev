"""Helpers for formatting subprocess errors."""
from __future__ import annotations

import subprocess


def format_process_error(error: OSError | subprocess.SubprocessError) -> str:
    if isinstance(error, subprocess.TimeoutExpired):
        return f"timeout ({error.timeout}s)"
    if isinstance(error, subprocess.CalledProcessError):
        return (
            (error.stderr or "").strip()
            or (error.stdout or "").strip()
            or f"exit status {error.returncode}"
        )
    return str(error)
