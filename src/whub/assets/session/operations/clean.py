import shutil
import subprocess
import sys
from pathlib import Path

import yaml


root, run_id = Path(sys.argv[1]), sys.argv[2]
path = root / ".whub" / "sessions" / f"{run_id}.yaml"
if not path.is_file():
    raise SystemExit(f"unknown run: {run_id}")
data = yaml.safe_load(path.read_text())
if data["state"] == "running":
    raise SystemExit(f"run is still running: {run_id}")
if data.get("tmux"):
    subprocess.run(
        [
            "tmux",
            "-S",
            data["tmux"]["socket"],
            "kill-session",
            "-t",
            f"={data['tmux']['session']}",
        ],
        capture_output=True,
    )
shutil.rmtree(root / ".whub" / "runs" / run_id, ignore_errors=True)
path.unlink()
