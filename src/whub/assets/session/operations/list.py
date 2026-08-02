import json
import sys
from pathlib import Path

import yaml


root = Path(sys.argv[1])
requested = sys.argv[2] if len(sys.argv) > 2 else None
paths = (
    [root / ".whub" / "sessions" / f"{requested}.yaml"]
    if requested
    else sorted((root / ".whub" / "sessions").glob("*.yaml"))
)
items = []
for path in paths:
    if not path.is_file():
        continue
    items.append(yaml.safe_load(path.read_text()))
print(json.dumps(items, default=str))
