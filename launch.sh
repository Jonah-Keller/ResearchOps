#!/bin/bash
# Open ResearchOps: reuse the server if it's already running, otherwise start it in
# the background (no Terminal window needed), then open the browser.
# The Dock icon made by tools/make_app.sh runs this.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; LOG="$HOME/Library/Logs/ResearchOps.log"
PORT="$(cat "$DIR/.port" 2>/dev/null)"
if [ -n "$PORT" ] && [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/data")" = "200" ]; then
  open "http://127.0.0.1:$PORT"; exit 0
fi
mkdir -p "$(dirname "$LOG")"
cd "$DIR" && nohup ./start.sh >> "$LOG" 2>&1 &
