#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null 2>&1 || {
  echo "whub session: python3 is required" >&2
  exit 1
}

launcher_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$launcher_dir/session-launcher.py" "$@"
