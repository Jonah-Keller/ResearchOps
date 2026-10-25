#!/usr/bin/env bash
# One-command install for ResearchOps (macOS).
#
#   curl -fsSL https://raw.githubusercontent.com/Jonah-Keller/ResearchOps/main/install.sh | bash
#
# Clones the repo to ~/ResearchOps, creates a fresh empty workspace, adds a
# ResearchOps icon to the Dock, starts the local server, and opens it in your browser. Safe to re-run: if the folder is
# already there it just pulls the latest code and starts up. Your data is never
# touched by an update.
set -euo pipefail

REPO="https://github.com/Jonah-Keller/ResearchOps.git"
DEST="${RESEARCHOPS_DIR:-$HOME/ResearchOps}"

# git and python3 come with Apple's free command line tools. If they're missing,
# start Apple's installer and ask the person to run this line again afterwards.
if ! xcode-select -p >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
  echo "One-time setup: macOS needs Apple's free developer tools."
  echo "A window will pop up — click Install, wait for it to finish (5–15 minutes),"
  echo "then paste the same install line into Terminal again."
  xcode-select --install 2>/dev/null || true
  exit 1
fi

if [ -d "$DEST/.git" ]; then
  echo "Updating existing install at $DEST …"
  git -C "$DEST" pull --ff-only
else
  echo "Installing to $DEST …"
  git clone --depth 1 "$REPO" "$DEST"
fi

chmod +x "$DEST/start.sh" "$DEST/launch.sh" "$DEST/tools/make_app.sh"
mkdir -p "$DEST/data"
[ -f "$DEST/data/projects.json" ] || cp "$DEST/seed/projects.json" "$DEST/data/projects.json"
"$DEST/tools/make_app.sh"
"$DEST/launch.sh"
echo
echo "Done. ResearchOps is opening in your browser."
echo "You can close this window. From now on, just click the ResearchOps icon in your Dock."
