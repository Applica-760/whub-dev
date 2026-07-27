"""List or remove verified AppleDouble sidecars below the current directory."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


if len(sys.argv) != 4 or sys.argv[1] not in {"--list", "--apply"}:
    fail("usage: cleanup_appledouble.py (--list|--apply) PREFIX MAGIC_HEX")

apply = sys.argv[1] == "--apply"
prefix = sys.argv[2]
magic = bytes.fromhex(sys.argv[3])
root = Path.cwd()
candidates: list[Path] = []

for directory, names, filenames in os.walk(root, followlinks=False):
    directory_path = Path(directory)
    names[:] = sorted(
        name
        for name in names
        if name != ".git" and not (directory_path / name).is_symlink()
    )
    for name in sorted(filenames):
        path = directory_path / name
        if not name.startswith(prefix) or path.is_symlink():
            continue
        try:
            with path.open("rb") as stream:
                is_apple_double = stream.read(len(magic)) == magic
        except OSError as error:
            fail(f"cannot inspect {path.relative_to(root)}: {error}")
        if is_apple_double:
            candidates.append(path)

for path in candidates:
    print(path.relative_to(root))

if not apply:
    raise SystemExit(0)

for path in candidates:
    try:
        with path.open("rb") as stream:
            if stream.read(len(magic)) != magic:
                fail(f"refusing changed sidecar: {path.relative_to(root)}")
        path.unlink()
    except OSError as error:
        fail(f"cannot remove {path.relative_to(root)}: {error}")
