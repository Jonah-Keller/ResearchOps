#!/usr/bin/env bash
# Start ResearchOps. Creates a fresh, empty workspace on first run.
#   ./start.sh          pick the first free port from 8765
#   ./start.sh 9000     use a specific port
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found."
  echo "On macOS, install Apple's command line tools:  xcode-select --install"
  exit 1
fi

mkdir -p data
if [ ! -f data/projects.json ]; then
  cp seed/projects.json data/projects.json
  echo "Created a fresh workspace → data/projects.json"
fi

# Pick a free port so a second copy (or a stale server) doesn't blow up on bind.
PORT="$(python3 - "${1:-8765}" <<'PY'
import socket, sys
start = int(sys.argv[1])
for p in range(start, start + 40):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", p)); print(p); break
        except OSError:
            continue
else:
    sys.exit("no free port in range")
PY
)"

echo "$PORT" > .port
( sleep 1; open "http://127.0.0.1:$PORT" >/dev/null 2>&1 || true ) &
exec python3 serve.py "$PORT"
