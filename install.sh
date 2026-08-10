#!/usr/bin/env bash
# One-command install for ResearchOps (macOS).
#
#   curl -fsSL https://raw.githubusercontent.com/Jonah-Keller/ResearchOps/main/install.sh | bash
#
# Clones the repo to ~/ResearchOps, creates a fresh empty workspace, starts the
# local server, and opens it in your browser. Safe to re-run: if the folder is
# already there it just pulls the latest code and starts up. Your data is never
# touched by an update.
set -euo pipefail

REPO="https://github.com/Jonah-Keller/ResearchOps.git"
DEST="${RESEARCHOPS_DIR:-$HOME/ResearchOps}"

if ! command -v git >/dev/null 2>&1; then
  echo "git not found. Install Apple's command line tools first:"
  echo "  xcode-select --install"
  exit 1
fi

if [ -d "$DEST/.git" ]; then
  echo "Updating existing install at $DEST …"
  git -C "$DEST" pull --ff-only
else
  echo "Installing to $DEST …"
  git clone --depth 1 "$REPO" "$DEST"
fi

chmod +x "$DEST/start.sh"
echo
echo "Done. Starting ResearchOps — leave this window open while you use it."
echo "To start it again later:  cd $DEST && ./start.sh"
echo
exec "$DEST/start.sh"
