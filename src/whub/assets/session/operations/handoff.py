import fcntl
import json
import os
import re
import sys
import tempfile
from pathlib import Path


root, run_id = Path(sys.argv[1]), sys.argv[2]
payload = json.load(sys.stdin)
runtime = root / ".whub"
descriptor = runtime / "sessions" / f"{run_id}.yaml"
if not descriptor.is_file() or descriptor.is_symlink():
    raise SystemExit(f"unknown run: {run_id}")
handoff = runtime / "handoff"
handoff.mkdir(parents=True, exist_ok=True, mode=0o700)
handoff.chmod(0o700)
path = handoff / "commands.md"
lock_path = handoff / "commands.lock"
lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
with os.fdopen(lock_fd, "r+") as lock:
    os.fchmod(lock.fileno(), 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX)
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise SystemExit(f"unexpected handoff path: {path}")
    existing = path.read_bytes() if path.exists() else b""
    command = payload["command"]
    fence_length = max(
        3,
        max((len(match.group()) for match in re.finditer(r"`+", command)), default=0)
        + 1,
    )
    fence = "`" * fence_length
    if not command.endswith("\n"):
        command += "\n"
    entry = (
        f"## {payload['timestamp']} | {run_id} | {payload['purpose']}\n\n"
        f"### 1. Linux GUI terminal\n\n"
        f"{fence}bash\n"
        f"bash .whub/session-launcher.sh {run_id}\n"
        f"{fence}\n\n"
        f"### 2. tmux session\n\n"
        f"{fence}bash\n{command}{fence}\n\n"
    ).encode()
    fd, name = tempfile.mkstemp(dir=handoff, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(entry + existing)
            stream.flush()
            os.fsync(stream.fileno())
        tmp.chmod(0o600)
        os.replace(tmp, path)
        directory_fd = os.open(handoff, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        tmp.unlink(missing_ok=True)
