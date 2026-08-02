import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required")


root = Path(sys.argv[1])
payload = json.load(sys.stdin)
runtime = root / ".whub"
sessions = runtime / "sessions"
runs = runtime / "runs"
for path in (runtime, sessions, runs):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
gitignore = root / ".gitignore"
start, end = "# whub session:start", "# whub session:end"
existing = gitignore.read_text() if gitignore.exists() else ""
block = f"{start}\n.whub/\n{end}\n"
if start not in existing and end not in existing:
    content = block + ("\n" + existing if existing else "")
elif existing.count(start) == existing.count(end) == 1 and existing.index(
    start
) < existing.index(end):
    content = (
        existing[: existing.index(start)]
        + block
        + existing[existing.index(end) + len(end) :].lstrip("\n")
    )
else:
    raise SystemExit("invalid whub session markers in .gitignore")


def replace(path: Path, text: str, mode: int) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        tmp.chmod(mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


if content != existing:
    replace(gitignore, content, 0o644)
for name in ("session-launcher.py", "session-launcher.sh"):
    asset = runtime / name
    content = payload["assets"][name]
    if not asset.exists() or asset.read_text() != content:
        replace(asset, content, 0o600)
prefix = payload["task"] or "adhoc"
pattern = re.compile(re.escape(prefix) + r"-r([0-9]+)\.yaml$")
number = max(
    (
        int(match.group(1))
        for path in sessions.glob(f"{prefix}-r*.yaml")
        if (match := pattern.match(path.name))
    ),
    default=0,
)
while True:
    number += 1
    run_id = f"{prefix}-r{number:03}"
    path = sessions / f"{run_id}.yaml"
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "schema_version": 1,
        "protocol_version": 1,
        "project": payload["project"],
        "task": payload["task"],
        "run_id": run_id,
        "state": "pending",
        "created_at": now,
        "updated_at": now,
        "tmux": None,
        "panes": [],
    }
    fd, name = tempfile.mkstemp(dir=sessions, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            yaml.safe_dump(data, stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        tmp.chmod(0o600)
        try:
            os.link(tmp, path)
            print(run_id)
            break
        except FileExistsError:
            continue
    finally:
        tmp.unlink(missing_ok=True)
