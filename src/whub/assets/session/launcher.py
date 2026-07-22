from __future__ import annotations

from datetime import datetime, timezone
import os
import fcntl
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:
    raise SystemExit("whub session: PyYAML is required")

PROTOCOL_VERSION = 1
root = Path.cwd().resolve()
runtime = root / ".whub"
sessions = runtime / "sessions"
helper = runtime / "session-launcher.py"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or data.get("protocol_version") != PROTOCOL_VERSION:
        raise SystemExit(f"whub session: invalid descriptor: {path}")
    return data


def save(path: Path, data: dict) -> None:
    data["updated_at"] = now()
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def tmux(
    socket: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["tmux", "-S", str(socket), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def descriptor_path(run_id: str) -> Path:
    path = sessions / f"{run_id}.yaml"
    if not path.is_file():
        raise SystemExit(f"whub session: unknown run: {run_id}")
    return path


def _sync(run_id: str) -> None:
    path = descriptor_path(run_id)
    data = load(path)
    metadata = data.get("tmux") or {}
    socket_value = metadata.get("socket")
    session = metadata.get("session")
    if (
        not isinstance(socket_value, str)
        or not socket_value
        or not isinstance(session, str)
        or not session
    ):
        raise SystemExit(f"whub session: missing tmux metadata: {run_id}")
    socket = Path(socket_value)
    result = tmux(
        socket,
        "list-panes",
        "-t",
        f"={session}",
        "-F",
        "#{pane_id}\t#{window_id}\t#{window_name}\t#{pane_index}"
        "\t#{pane_dead}\t#{pane_dead_status}\t#{pane_dead_signal}",
        check=False,
    )
    if result.returncode:
        data["state"] = "interrupted"
        save(path, data)
        return

    known = {pane["pane_id"] for pane in data.get("panes", [])}
    pane_dir = runtime / "runs" / run_id / "panes"
    pane_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    pane_dir.chmod(0o700)
    panes = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 7:
            continue
        pane_id, window_id, window_name, pane_index, dead, status, signal = fields
        transcript = pane_dir / f"{pane_id.lstrip('%')}.log"
        transcript.touch(mode=0o600, exist_ok=True)
        transcript.chmod(0o600)
        if pane_id not in known:
            tmux(
                socket,
                "pipe-pane",
                "-o",
                "-t",
                pane_id,
                f"cat >> {shlex.quote(str(transcript))}",
                check=False,
            )
        panes.append(
            {
                "pane_id": pane_id,
                "window_id": window_id,
                "window_name": window_name,
                "pane_index": int(pane_index),
                "transcript": transcript.relative_to(root).as_posix(),
                "dead": dead == "1",
                "dead_status": int(status) if status else None,
                "dead_signal": int(signal) if signal else None,
            }
        )
    data["panes"] = panes
    if panes and all(pane["dead"] for pane in panes):
        if any(pane["dead_signal"] is not None for pane in panes):
            data["state"] = "interrupted"
        elif any((pane["dead_status"] or 0) != 0 for pane in panes):
            data["state"] = "failed"
        else:
            data["state"] = "completed"
    save(path, data)


def sync(run_id: str) -> None:
    lock_path = runtime / "runs" / run_id / "sync.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock_path.open("a") as lock:
        lock_path.chmod(0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        _sync(run_id)


def select(requested: str | None) -> tuple[Path, dict]:
    if requested:
        path = descriptor_path(requested)
        data = load(path)
        if data.get("state") not in {"pending", "running"}:
            raise SystemExit(f"whub session: run is not attachable: {requested}")
        return path, data
    pending = [
        (path, data)
        for path in sorted(sessions.glob("*.yaml"))
        if (data := load(path)).get("state") == "pending"
    ]
    if not pending:
        raise SystemExit("whub session: no matching pending run")
    if len(pending) > 1:
        runs = ", ".join(data["run_id"] for _, data in pending)
        raise SystemExit(f"whub session: multiple pending runs; specify one: {runs}")
    return pending[0]


def start(requested: str | None) -> None:
    if shutil.which("tmux") is None:
        raise SystemExit("whub session: tmux is required")
    path, data = select(requested)
    run_id = data["run_id"]
    if data["state"] == "running":
        metadata = data.get("tmux") or {}
        socket_value = metadata.get("socket")
        session = metadata.get("session")
        if (
            isinstance(socket_value, str)
            and socket_value
            and isinstance(session, str)
            and session
        ):
            socket = Path(socket_value)
            if (
                tmux(socket, "has-session", "-t", f"={session}", check=False).returncode
                == 0
            ):
                attach(socket, session)
        data["state"] = "interrupted"
        save(path, data)
        raise SystemExit(
            f"whub session: running session is no longer available: {run_id}"
        )
    socket = runtime / "tmux.sock"
    data["state"] = "running"
    data["tmux"] = {"socket": str(socket), "session": run_id}
    save(path, data)
    try:
        if socket.exists() and tmux(socket, "list-sessions", check=False).returncode:
            socket.unlink(missing_ok=True)
        tmux(
            socket,
            "start-server",
            ";",
            "set-option",
            "-g",
            "history-limit",
            "50000",
            ";",
            "set-option",
            "-g",
            "-w",
            "remain-on-exit",
            "on",
            ";",
            "new-session",
            "-d",
            "-s",
            run_id,
            "-c",
            str(root),
        )
        for option, value in (
            ("@whub_project", data["project"]),
            ("@whub_task", data.get("task") or ""),
            ("@whub_run", run_id),
        ):
            tmux(socket, "set-option", "-t", run_id, option, value)
        command = (
            shlex.join(["cd", str(root)])
            + " && "
            + shlex.join(["python3", str(helper), "__sync", run_id])
        )
        hook = f"run-shell -b {shlex.quote(command)}"
        for name in (
            "after-new-window",
            "after-split-window",
            "pane-exited",
            "pane-died",
        ):
            tmux(socket, "set-hook", "-t", run_id, name, hook)
        sync(run_id)
    except (OSError, subprocess.CalledProcessError) as error:
        data = load(path)
        data["state"] = "failed"
        save(path, data)
        detail = (
            f"{shlex.join(error.cmd)}: {error.stderr.strip()}"
            if isinstance(error, subprocess.CalledProcessError)
            else str(error)
        )
        raise SystemExit(f"whub session: failed to start tmux: {detail}") from error
    attach(socket, run_id)


def attach(socket: Path, session: str) -> None:
    os.execvp(
        "tmux",
        ["tmux", "-S", str(socket), "attach-session", "-t", f"={session}"],
    )


args = sys.argv[1:]
if args[:1] == ["__sync"]:
    if len(args) != 2:
        raise SystemExit("whub session: invalid sync invocation")
    sync(args[1])
else:
    if len(args) > 1:
        raise SystemExit("usage: bash .whub/session-launcher.sh [RUN]")
    if not sys.stdin.isatty():
        raise SystemExit("whub session: a terminal is required")
    start(args[0] if args else None)
